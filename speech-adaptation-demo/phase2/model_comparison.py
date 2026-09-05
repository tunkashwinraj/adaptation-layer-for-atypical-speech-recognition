import asyncio
import logging
import os
import time
from typing import Dict, List

from openai import OpenAI

from asr_processor import personalized_asr
from utils import load_audio_bytes
from analytics import wer

# Optional: Google Cloud Speech (requires google-cloud-speech + GOOGLE_APPLICATION_CREDENTIALS)
try:
    from google.cloud import speech as google_speech
    _GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    google_speech = None
    _GOOGLE_SPEECH_AVAILABLE = False

LOG = logging.getLogger(__name__)


class ModelComparator:
    def __init__(self):
        self.openai = OpenAI()

    async def compare_all_models(self, audio_path: str, vocab: List[dict], ground_truth: str = None):
        tasks = [
            asyncio.to_thread(self._run_deepgram, audio_path, vocab),
            asyncio.to_thread(self._run_whisper, audio_path),
        ]
        if _GOOGLE_SPEECH_AVAILABLE and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            tasks.append(asyncio.to_thread(self._run_google, audio_path))
        else:
            if not _GOOGLE_SPEECH_AVAILABLE:
                LOG.info("Google Cloud Speech skipped (install google-cloud-speech for multi-model comparison).")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        outputs = []
        for r in results:
            if isinstance(r, Exception):
                outputs.append({"error": str(r)})
            else:
                outputs.append(r)
        return self.analyze_results(outputs, ground_truth)

    def _run_deepgram(self, audio_path: str, vocab: List[dict]):
        start = time.time()
        result = personalized_asr(audio_path, vocab)
        ms = (time.time() - start) * 1000
        return {
            "model": "deepgram-nova-2",
            "transcript": result["transcript"],
            "confidence": result["confidence"],
            "latency_ms": ms,
            "cost_usd": None,
        }

    def _run_whisper(self, audio_path: str):
        start = time.time()
        with open(audio_path, "rb") as f:
            response = self.openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        ms = (time.time() - start) * 1000
        return {
            "model": "openai-whisper-1",
            "transcript": response.text,
            "confidence": None,
            "latency_ms": ms,
            "cost_usd": None,
        }

    def _run_google(self, audio_path: str):
        if not _GOOGLE_SPEECH_AVAILABLE or google_speech is None:
            return {"error": "Google Cloud Speech not installed (pip install google-cloud-speech)."}
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return {"error": "GOOGLE_APPLICATION_CREDENTIALS not set."}
        start = time.time()
        try:
            audio_bytes, content_type = load_audio_bytes(audio_path)
            client = google_speech.SpeechClient()
            audio = google_speech.RecognitionAudio(content=audio_bytes)
            config = google_speech.RecognitionConfig(
                language_code="en-US",
                enable_automatic_punctuation=True,
                encoding=google_speech.RecognitionConfig.AudioEncoding.LINEAR16
                if "wav" in (content_type or "")
                else google_speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
            )
            response = client.recognize(config=config, audio=audio)
            transcript = " ".join(r.alternatives[0].transcript for r in response.results)
        except Exception as e:
            return {"error": f"Google STT: {e}"}
        ms = (time.time() - start) * 1000
        return {
            "model": "google-stt",
            "transcript": transcript,
            "confidence": None,
            "latency_ms": ms,
            "cost_usd": None,
        }

    def analyze_results(self, results: List[Dict], ground_truth: str = None):
        enriched = []
        for r in results:
            if "error" in r:
                enriched.append(r)
                continue
            w = None
            if ground_truth:
                w = wer(ground_truth, r.get("transcript", ""))
            enriched.append({**r, "wer": w})
        return enriched

    def determine_best_model(self, results: List[Dict]):
        candidates = [r for r in results if "error" not in r]
        if not candidates:
            return None
        # Prefer lowest WER if present, else highest confidence
        with_wer = [r for r in candidates if r.get("wer") is not None]
        if with_wer:
            return min(with_wer, key=lambda r: r["wer"])
        return max(candidates, key=lambda r: (r.get("confidence") or 0))

    def model_ensemble(self, results: List[Dict]) -> str:
        candidates = [r for r in results if "error" not in r]
        if not candidates:
            return ""
        # Simple majority vote on tokens
        token_lists = [r.get("transcript", "").split() for r in candidates]
        if not token_lists:
            return ""
        # Use the longest as base
        base = max(token_lists, key=len)
        out = []
        for i, tok in enumerate(base):
            votes = []
            for tl in token_lists:
                if i < len(tl):
                    votes.append(tl[i])
            if votes:
                out.append(max(set(votes), key=votes.count))
        return " ".join(out)
