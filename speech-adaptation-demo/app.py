import difflib
import logging
import os
import tempfile
from typing import Optional
from urllib.request import urlopen, Request

import gradio as gr
import pandas as pd
import soundfile as sf
from dotenv import load_dotenv

from asr_processor import baseline_asr, personalized_asr
from analytics import (
    cer,
    cosine_similarity,
    diff_ops,
    grammar_flags,
    jaccard_similarity,
    readability_stats,
    timing_stats,
    token_overlap_ratio,
    wer,
    confidence_stats,
)
from semantic_repair import semantic_repair
from utils import parse_custom_vocab


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger("speech-adaptation-demo")


DEFAULT_VOCAB = """Atorvastatin:2.0
Calgary:1.5
Spearia:2.0
TripGenius:1.5
"""

SAMPLE_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "sample_audio")


AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a"}


def _list_demo_audio():
    if not os.path.isdir(SAMPLE_AUDIO_DIR):
        return []
    files = []
    for name in sorted(os.listdir(SAMPLE_AUDIO_DIR)):
        if name.startswith("."):
            continue
        path = os.path.join(SAMPLE_AUDIO_DIR, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS:
            files.append(path)
        elif os.path.isdir(path):
            for sub in sorted(os.listdir(path)):
                if sub.startswith("."):
                    continue
                if os.path.splitext(sub)[1].lower() in AUDIO_EXTENSIONS:
                    files.append(os.path.join(path, sub))
    return files


def _ensure_env() -> None:
    load_dotenv()
    missing = []
    if not os.getenv("DEEPGRAM_API_KEY"):
        missing.append("DEEPGRAM_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if missing:
        raise RuntimeError(f"Missing API keys in .env: {', '.join(missing)}")


def _persist_audio(audio_input):
    if audio_input is None:
        return None, None
    if isinstance(audio_input, str):
        return audio_input, None
    if isinstance(audio_input, (list, tuple)) and len(audio_input) == 2:
        sample_rate, data = audio_input
        tmp = tempfile.NamedTemporaryFile(prefix="gradio_audio_", suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        sf.write(tmp_path, data, sample_rate)
        return tmp_path, tmp_path
    return None, None


def _extract_upload_path(uploaded_file) -> Optional[str]:
    if uploaded_file is None:
        return None
    if isinstance(uploaded_file, str):
        return uploaded_file
    if isinstance(uploaded_file, dict) and "path" in uploaded_file:
        return uploaded_file["path"]
    if hasattr(uploaded_file, "name"):
        return uploaded_file.name
    if hasattr(uploaded_file, "path"):
        return uploaded_file.path
    return None


def _download_audio_url(url: str):
    """Download audio from a direct URL to a temp file. Returns (path, temp_path) or (None, None)."""
    if not url or not str(url).strip():
        return None, None
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        return None, None
    try:
        req = Request(url, headers={"User-Agent": "SpeechAdaptationDemo/1.0"})
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
            content_type = (resp.headers.get("Content-Type") or "").lower()
        ext = ".wav"
        if ".mp3" in url.lower() or "audio/mpeg" in content_type:
            ext = ".mp3"
        elif ".flac" in url.lower() or "audio/flac" in content_type:
            ext = ".flac"
        elif ".m4a" in url.lower():
            ext = ".m4a"
        tmp = tempfile.NamedTemporaryFile(prefix="url_audio_", suffix=ext, delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name, tmp.name
    except Exception as e:
        LOGGER.warning("Failed to download audio from URL: %s", e)
        return None, None


def run_pipeline(audio_input, uploaded_file, demo_audio_path: str, audio_url: str, vocab_text: str, context_hints: str, ground_truth: str):
    audio_path = None
    temp_path = None
    if audio_url and str(audio_url).strip():
        audio_path, temp_path = _download_audio_url(audio_url)
    if not audio_path:
        audio_path = demo_audio_path or None
    if not audio_path:
        upload_path = _extract_upload_path(uploaded_file)
        if upload_path:
            audio_path = upload_path
        else:
            audio_path, temp_path = _persist_audio(audio_input)
    if not audio_path:
        raise gr.Error("Please upload/record audio or select a demo file.")

    _ensure_env()

    custom_vocab = parse_custom_vocab(vocab_text)
    LOGGER.info("Custom vocabulary loaded: %s", custom_vocab)

    try:
        baseline = baseline_asr(audio_path)
        personalized = personalized_asr(audio_path, custom_vocab)
        repaired = semantic_repair(personalized["transcript"], context_hints)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                LOGGER.warning("Failed to delete temp audio file %s", temp_path)

    comparison = pd.DataFrame(
        [
            {
                "Stage": "Baseline ASR",
                "Transcript": baseline["transcript"],
                "Confidence": round(baseline["confidence"], 4),
            },
            {
                "Stage": "Personalized ASR",
                "Transcript": personalized["transcript"],
                "Confidence": round(personalized["confidence"], 4),
            },
            {
                "Stage": "Semantic Repair",
                "Transcript": repaired,
                "Confidence": "",
            },
        ]
    )

    diff_html = build_visual_diff(
        baseline["transcript"],
        personalized["transcript"],
        repaired,
    )

    # Analytics
    baseline_conf = confidence_stats(baseline["word_timings"])
    personalized_conf = confidence_stats(personalized["word_timings"])
    baseline_timing = timing_stats(baseline["word_timings"])
    personalized_timing = timing_stats(personalized["word_timings"])

    baseline_read = readability_stats(baseline["transcript"])
    personalized_read = readability_stats(personalized["transcript"])
    repaired_read = readability_stats(repaired)

    baseline_grammar = grammar_flags(baseline["transcript"])
    personalized_grammar = grammar_flags(personalized["transcript"])
    repaired_grammar = grammar_flags(repaired)

    bp_counts, bp_replacements = diff_ops(baseline["transcript"], personalized["transcript"])
    pr_counts, pr_replacements = diff_ops(personalized["transcript"], repaired)

    similarity_rows = [
        {
            "Comparison": "Baseline vs Personalized",
            "Jaccard": round(jaccard_similarity(baseline["transcript"], personalized["transcript"]), 4),
            "Cosine": round(cosine_similarity(baseline["transcript"], personalized["transcript"]), 4),
            "Token Overlap": round(token_overlap_ratio(baseline["transcript"], personalized["transcript"]), 4),
        },
        {
            "Comparison": "Personalized vs Repaired",
            "Jaccard": round(jaccard_similarity(personalized["transcript"], repaired), 4),
            "Cosine": round(cosine_similarity(personalized["transcript"], repaired), 4),
            "Token Overlap": round(token_overlap_ratio(personalized["transcript"], repaired), 4),
        },
        {
            "Comparison": "Baseline vs Repaired",
            "Jaccard": round(jaccard_similarity(baseline["transcript"], repaired), 4),
            "Cosine": round(cosine_similarity(baseline["transcript"], repaired), 4),
            "Token Overlap": round(token_overlap_ratio(baseline["transcript"], repaired), 4),
        },
    ]
    similarity_df = pd.DataFrame(similarity_rows)

    accuracy_rows = []
    if ground_truth and ground_truth.strip():
        accuracy_rows = [
            {
                "Stage": "Baseline",
                "WER": round(wer(ground_truth, baseline["transcript"]) or 0.0, 4),
                "CER": round(cer(ground_truth, baseline["transcript"]) or 0.0, 4),
            },
            {
                "Stage": "Personalized",
                "WER": round(wer(ground_truth, personalized["transcript"]) or 0.0, 4),
                "CER": round(cer(ground_truth, personalized["transcript"]) or 0.0, 4),
            },
            {
                "Stage": "Repaired",
                "WER": round(wer(ground_truth, repaired) or 0.0, 4),
                "CER": round(cer(ground_truth, repaired) or 0.0, 4),
            },
        ]
    accuracy_df = pd.DataFrame(accuracy_rows)

    confidence_df = pd.DataFrame(
        [
            {"Stage": "Baseline", **baseline_conf},
            {"Stage": "Personalized", **personalized_conf},
        ]
    )

    timing_df = pd.DataFrame(
        [
            {"Stage": "Baseline", **baseline_timing},
            {"Stage": "Personalized", **personalized_timing},
        ]
    )

    readability_df = pd.DataFrame(
        [
            {"Stage": "Baseline", **baseline_read},
            {"Stage": "Personalized", **personalized_read},
            {"Stage": "Repaired", **repaired_read},
        ]
    )

    grammar_df = pd.DataFrame(
        [
            {"Stage": "Baseline", **baseline_grammar},
            {"Stage": "Personalized", **personalized_grammar},
            {"Stage": "Repaired", **repaired_grammar},
        ]
    )

    error_df = pd.DataFrame(
        [
            {"Comparison": "Baseline -> Personalized", **bp_counts},
            {"Comparison": "Personalized -> Repaired", **pr_counts},
        ]
    )

    # Repair impact
    pr_counts_for_edit, _ = diff_ops(personalized["transcript"], repaired)
    edit_dist = pr_counts_for_edit["replace"] + pr_counts_for_edit["insert"] + pr_counts_for_edit["delete"]
    base_len = max(1, len(personalized["transcript"].split()))
    repair_impact = pd.DataFrame(
        [
            {
                "Metric": "Edit Distance (Personalized->Repaired)",
                "Value": edit_dist,
            },
            {
                "Metric": "Percent Tokens Changed",
                "Value": round(edit_dist / base_len, 4),
            },
        ]
    )

    confusion_pairs = {
        "baseline_to_personalized": bp_replacements[:50],
        "personalized_to_repaired": pr_replacements[:50],
    }

    return (
        baseline["transcript"],
        baseline["word_timings"],
        personalized["transcript"],
        personalized["word_timings"],
        repaired,
        comparison,
        diff_html,
        similarity_df,
        accuracy_df,
        confidence_df,
        timing_df,
        readability_df,
        grammar_df,
        error_df,
        repair_impact,
        confusion_pairs,
    )


def _token_diff_html(source: str, target: str) -> str:
    source_tokens = source.split()
    target_tokens = target.split()
    matcher = difflib.SequenceMatcher(a=source_tokens, b=target_tokens)
    out = []
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "equal":
            out.extend(source_tokens[a0:a1])
        elif op == "delete":
            deleted = " ".join(source_tokens[a0:a1])
            out.append(f"<span class='diff-del'>{deleted}</span>")
        elif op == "insert":
            inserted = " ".join(target_tokens[b0:b1])
            out.append(f"<span class='diff-add'>{inserted}</span>")
        elif op == "replace":
            deleted = " ".join(source_tokens[a0:a1])
            inserted = " ".join(target_tokens[b0:b1])
            out.append(f"<span class='diff-del'>{deleted}</span>")
            out.append(f"<span class='diff-add'>{inserted}</span>")
    return " ".join(out)


def build_visual_diff(baseline: str, personalized: str, repaired: str) -> str:
    baseline = baseline or ""
    personalized = personalized or ""
    repaired = repaired or ""
    return f"""
    <div class="diff-grid">
      <div class="diff-card">
        <div class="diff-title">Baseline -> Personalized</div>
        <div class="diff-body">{_token_diff_html(baseline, personalized)}</div>
      </div>
      <div class="diff-card">
        <div class="diff-title">Personalized -> Semantic Repair</div>
        <div class="diff-body">{_token_diff_html(personalized, repaired)}</div>
      </div>
    </div>
    """


CSS_OVERRIDES = """
.diff-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.diff-card { border: 1px solid #e5e5e5; border-radius: 10px; padding: 12px; background: #fafafa; }
.diff-title { font-weight: 600; margin-bottom: 8px; }
.diff-body { line-height: 1.6; }
.diff-add { background: #e6f4ea; color: #1e4620; padding: 2px 4px; border-radius: 4px; }
.diff-del { background: #fce8e6; color: #a50e0e; padding: 2px 4px; border-radius: 4px; text-decoration: line-through; }
@media (max-width: 900px) { .diff-grid { grid-template-columns: 1fr; } }
"""


with gr.Blocks(title="Personal Speech Adaptation Layer Demo") as demo:
    gr.Markdown(
        """
        # Personal Speech Adaptation Layer Demo
        This prototype demonstrates a 4-stage pipeline: baseline ASR, personalized ASR with vocabulary biasing,
        LLM semantic repair, and side-by-side comparison. Use it with atypical speech samples to observe improvements.
        """
    )

    with gr.Row():
        audio_input = gr.Audio(
            label="Record Audio (Mic)",
            type="numpy",
            sources=["microphone"],
        )
        context_input = gr.Textbox(
            label="Domain Hints (optional)",
            lines=6,
            placeholder="e.g., medical visit, travel booking, medications, family names",
        )

    audio_url_input = gr.Textbox(
        label="Or paste direct audio URL (WAV/MP3/FLAC)",
        placeholder="https://example.com/sample.wav",
        lines=1,
    )

    uploaded_audio = gr.File(
        label="Upload Audio File",
        file_types=[".wav", ".flac", ".mp3", ".m4a"],
    )

    demo_audio_choices = _list_demo_audio()
    demo_audio = gr.Dropdown(
        label="Built-in Demo Audio",
        choices=demo_audio_choices,
        value=demo_audio_choices[0] if demo_audio_choices else None,
        interactive=True,
        allow_custom_value=False,
    )

    vocab_input = gr.Textbox(
        label="Custom Vocabulary (one per line as word:boost)",
        lines=6,
        value=DEFAULT_VOCAB,
    )
    ground_truth_input = gr.Textbox(
        label="Optional Ground Truth Transcript (for WER/CER)",
        lines=4,
        placeholder="Paste the known correct transcript here (optional)",
    )

    run_btn = gr.Button("Run Speech Adaptation Pipeline", variant="primary")

    with gr.Row():
        baseline_out = gr.Textbox(label="Baseline ASR Transcript", lines=4)
        personalized_out = gr.Textbox(label="Personalized ASR Transcript", lines=4)
        repaired_out = gr.Textbox(label="Semantic Repair Output", lines=4)

    with gr.Row():
        baseline_words = gr.JSON(label="Baseline Word Timings")
        personalized_words = gr.JSON(label="Personalized Word Timings")

    comparison_table = gr.Dataframe(
        label="Side-by-Side Comparison",
        interactive=False,
        wrap=True,
    )

    diff_view = gr.HTML(label="Visual Diff")

    similarity_table = gr.Dataframe(label="Similarity Metrics", interactive=False, wrap=True)
    accuracy_table = gr.Dataframe(label="WER/CER vs Ground Truth", interactive=False, wrap=True)
    confidence_table = gr.Dataframe(label="Confidence Metrics", interactive=False, wrap=True)
    timing_table = gr.Dataframe(label="Timing Metrics", interactive=False, wrap=True)
    readability_table = gr.Dataframe(label="Readability Metrics", interactive=False, wrap=True)
    grammar_table = gr.Dataframe(label="Grammar Flags", interactive=False, wrap=True)
    error_table = gr.Dataframe(label="Error Analysis", interactive=False, wrap=True)
    repair_table = gr.Dataframe(label="Repair Impact", interactive=False, wrap=True)
    confusion_json = gr.JSON(label="Top Replacement Pairs")

    run_btn.click(
        run_pipeline,
        inputs=[audio_input, uploaded_audio, demo_audio, audio_url_input, vocab_input, context_input, ground_truth_input],
        outputs=[
            baseline_out,
            baseline_words,
            personalized_out,
            personalized_words,
            repaired_out,
            comparison_table,
            diff_view,
            similarity_table,
            accuracy_table,
            confidence_table,
            timing_table,
            readability_table,
            grammar_table,
            error_table,
            repair_table,
            confusion_json,
        ],
    )


if __name__ == "__main__":
    demo.launch(
        css=CSS_OVERRIDES,
        allowed_paths=[SAMPLE_AUDIO_DIR, tempfile.gettempdir()],
    )
