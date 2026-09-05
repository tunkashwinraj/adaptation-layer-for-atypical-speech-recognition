import logging
import os
from typing import Dict, List

from deepgram import DeepgramClient
from deepgram.core.api_error import ApiError
from dotenv import load_dotenv

from utils import load_audio_bytes

LOGGER = logging.getLogger(__name__)


def _build_keywords(custom_vocabulary: List[dict]) -> List[str]:
    keywords = []
    for entry in custom_vocabulary or []:
        word = entry.get("word")
        boost = entry.get("boost", 1.5)
        if not word:
            continue
        keywords.append(f"{word}:{boost}")
    return keywords


def _transcribe(audio_file_path: str, keywords: List[str] = None) -> Dict:
    audio_bytes, _content_type = load_audio_bytes(audio_file_path)
    load_dotenv()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPGRAM_API_KEY in environment or .env.")
    client = DeepgramClient(api_key=api_key)

    request_options = {
        "model": "nova-2",
        "language": "en",
        "punctuate": True,
        "diarize": False,
        # Keyword boosting is done by passing keyword:intensifier strings.
        "keywords": keywords or [],
    }

    LOGGER.info("Deepgram request options: %s", request_options)
    try:
        response = client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            **request_options,
        )
        LOGGER.info(
            "Deepgram response received. Transcript length=%s",
            len(response.results.channels[0].alternatives[0].transcript or ""),
        )
    except ApiError as exc:
        LOGGER.exception("Deepgram API error: %s", exc)
        raise RuntimeError(f"Deepgram API error: {exc}") from exc
    except Exception as exc:
        LOGGER.exception("Unexpected Deepgram error: %s", exc)
        raise RuntimeError(f"Unexpected Deepgram error: {exc}") from exc

    alternatives = response.results.channels[0].alternatives
    if not alternatives:
        return {"transcript": "", "confidence": 0.0, "word_timings": []}

    best = alternatives[0]
    word_timings = []
    for w in best.words or []:
        word_timings.append(
            {
                "word": w.word,
                "start": w.start,
                "end": w.end,
                "confidence": w.confidence,
            }
        )

    return {
        "transcript": best.transcript or "",
        "confidence": float(best.confidence or 0.0),
        "word_timings": word_timings,
    }


def baseline_asr(audio_file_path: str) -> Dict:
    """
    Baseline ASR with no custom parameters.
    """
    return _transcribe(audio_file_path, keywords=None)


def personalized_asr(audio_file_path: str, custom_vocabulary: List[dict]) -> Dict:
    """
    Personalized ASR using keyword boosting.
    """
    keywords = _build_keywords(custom_vocabulary)
    return _transcribe(audio_file_path, keywords=keywords)
