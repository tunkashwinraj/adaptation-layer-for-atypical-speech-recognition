import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Optional
from urllib.request import urlopen, Request

import gradio as gr
import pandas as pd
import soundfile as sf
from dotenv import load_dotenv

from asr_processor import baseline_asr, personalized_asr
from semantic_repair import semantic_repair
from analytics import (
    cer,
    confidence_stats,
    diff_ops,
    grammar_flags,
    jaccard_similarity,
    readability_stats,
    timing_stats,
    token_overlap_ratio,
    wer,
    cosine_similarity,
)
from utils import parse_custom_vocab

from phase2 import init_db
from phase2.continual_learning import CorrectionManager
from phase2.pronunciation_engine import PronunciationMapper, pattern_summary
from phase2.model_comparison import ModelComparator
from phase2.advanced_metrics import metrics_bundle
from phase2.profile_manager import ProfileManager
from phase2.adaptive_interaction import AdaptiveInteractionManager
from phase2.analytics_dashboard import AnalyticsDashboard
from phase2.export_system import ExportManager
from phase2.db import Session as SessionRow, ModelPerformance, get_session

# Optional: Phase 3 thesis export (requires scipy, matplotlib, numpy)
try:
    from phase3.thesis_export import ThesisGenerator
except ImportError as e:
    ThesisGenerator = None
    logging.getLogger("speech-adaptation-demo-phase2").warning(
        "Thesis export unavailable: %s (pip install scipy matplotlib)", e
    )


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger("speech-adaptation-demo-phase2")


DEFAULT_VOCAB = """Atorvastatin:2.0
Calgary:1.5
Spearia:2.0
TripGenius:1.5
"""

SAMPLE_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "sample_audio")


AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a"}


def _list_demo_audio():
    files = []
    if os.path.isdir(SAMPLE_AUDIO_DIR):
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
    # Optional: include external UASpeech path (e.g. D:\research\data\UASpeech\audio\original)
    external = os.environ.get("UASPEECH_AUDIO_DIR", "").strip()
    if external and os.path.isdir(external):
        for name in sorted(os.listdir(external)):
            if name.startswith("."):
                continue
            path = os.path.join(external, name)
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


def _record_session(user_id: str, metrics: dict, correction_count: int = 0):
    session = get_session()
    try:
        session_id = f"sess_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        row = SessionRow(
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            total_utterances=1,
            correction_count=correction_count,
            metrics=metrics,
        )
        session.add(row)
        session.commit()
    finally:
        session.close()
    return session_id


def _record_model_perf(user_id: str, results):
    session = get_session()
    try:
        for r in results:
            if "error" in r:
                continue
            session.add(
                ModelPerformance(
                    user_id=user_id,
                    model_name=r.get("model"),
                    wer=r.get("wer"),
                    semscore=r.get("semscore"),
                    latency_ms=r.get("latency_ms"),
                    cost_usd=r.get("cost_usd"),
                )
            )
        session.commit()
    finally:
        session.close()


def run_pipeline_phase2(user_id: str, audio_input, uploaded_file, demo_audio_path: str, audio_url: str,
                        audio_path_text: str, vocab_text: str, context_hints: str, ground_truth: str, task_context: str,
                        enable_learning: bool, enable_adaptive: bool):
    _ensure_env()
    user_id = parse_profile_id(user_id)
    audio_path = None
    temp_path = None
    if audio_url and str(audio_url).strip():
        audio_path, temp_path = _download_audio_url(audio_url)
    if not audio_path and audio_path_text and str(audio_path_text).strip():
        p = str(audio_path_text).strip()
        if os.path.isfile(p) and p.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):
            audio_path = p
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

    custom_vocab = parse_custom_vocab(vocab_text)
    baseline = baseline_asr(audio_path)
    personalized = personalized_asr(audio_path, custom_vocab)
    repaired = semantic_repair(personalized["transcript"], context_hints)

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
    pr_counts_for_edit = pr_counts
    edit_dist = pr_counts_for_edit["replace"] + pr_counts_for_edit["insert"] + pr_counts_for_edit["delete"]
    base_len = max(1, len(personalized["transcript"].split()))

    similarity_df = pd.DataFrame(
        [
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
    )

    accuracy_rows = []
    if ground_truth and ground_truth.strip():
        accuracy_rows = [
            {"Stage": "Baseline", "WER": round(wer(ground_truth, baseline["transcript"]) or 0.0, 4),
             "CER": round(cer(ground_truth, baseline["transcript"]) or 0.0, 4)},
            {"Stage": "Personalized", "WER": round(wer(ground_truth, personalized["transcript"]) or 0.0, 4),
             "CER": round(cer(ground_truth, personalized["transcript"]) or 0.0, 4)},
            {"Stage": "Repaired", "WER": round(wer(ground_truth, repaired) or 0.0, 4),
             "CER": round(cer(ground_truth, repaired) or 0.0, 4)},
        ]
    accuracy_df = pd.DataFrame(accuracy_rows)

    confidence_df = pd.DataFrame(
        [{"Stage": "Baseline", **baseline_conf}, {"Stage": "Personalized", **personalized_conf}]
    )
    timing_df = pd.DataFrame(
        [{"Stage": "Baseline", **baseline_timing}, {"Stage": "Personalized", **personalized_timing}]
    )
    readability_df = pd.DataFrame(
        [{"Stage": "Baseline", **baseline_read}, {"Stage": "Personalized", **personalized_read},
         {"Stage": "Repaired", **repaired_read}]
    )
    grammar_df = pd.DataFrame(
        [{"Stage": "Baseline", **baseline_grammar}, {"Stage": "Personalized", **personalized_grammar},
         {"Stage": "Repaired", **repaired_grammar}]
    )
    error_df = pd.DataFrame(
        [{"Comparison": "Baseline -> Personalized", **bp_counts},
         {"Comparison": "Personalized -> Repaired", **pr_counts}]
    )
    repair_impact = pd.DataFrame(
        [{"Metric": "Edit Distance (Personalized->Repaired)", "Value": edit_dist},
         {"Metric": "Percent Tokens Changed", "Value": round(edit_dist / base_len, 4)}]
    )
    confusion_pairs = {
        "baseline_to_personalized": bp_replacements[:50],
        "personalized_to_repaired": pr_replacements[:50],
    }

    comparison = pd.DataFrame(
        [
            {"Stage": "Baseline ASR", "Transcript": baseline["transcript"],
             "Confidence": round(baseline["confidence"], 4)},
            {"Stage": "Personalized ASR", "Transcript": personalized["transcript"],
             "Confidence": round(personalized["confidence"], 4)},
            {"Stage": "Semantic Repair", "Transcript": repaired, "Confidence": ""},
        ]
    )

    # Advanced metrics (SemScore, MER, Task Success, LATTEScore if task_context provided)
    adv = metrics_bundle(ground_truth or repaired, repaired, task_context=task_context)
    adv_df = pd.DataFrame([adv])

    # Persist session metrics, including per-stage WERs when ground truth is available
    session_metrics: dict = {
        "mer": adv.get("mer"),
        "semscore": adv.get("semscore"),
        "task_success": adv.get("task_success_rate"),
    }
    if not accuracy_df.empty:
        try:
            def _stage_wer(stage: str) -> float | None:
                row = accuracy_df.loc[accuracy_df["Stage"] == stage]
                if row.empty:
                    return None
                return float(row["WER"].iloc[0])

            session_metrics["baseline_wer"] = _stage_wer("Baseline")
            session_metrics["personalized_wer"] = _stage_wer("Personalized")
            session_metrics["repaired_wer"] = _stage_wer("Repaired")
        except Exception:
            # Keep going even if dataframe structure changes
            pass

    # Record session metrics (and get a session id for interaction logging)
    session_id = None
    if user_id:
        session_id = _record_session(user_id, session_metrics, 0)

    # Adaptive interaction
    interaction = {}
    frustration_display = ""
    confirmation_prompt = ""
    fallback_message = ""
    if enable_adaptive and user_id:
        interaction = AdaptiveInteractionManager().detect_frustration(
            {
                "user_id": user_id,
                "current_metric": session_metrics.get("mer"),
                "session_id": session_id,
            }
        )
        score = float(interaction.get("score", 0.0) or 0.0)
        mode = interaction.get("mode", "INTEGRATION")
        if score > 0.7:
            emoji = "😟"
            confirmation_prompt = "High frustration detected. Let's confirm step by step: is this transcript correct?"
            fallback_message = "If this is still wrong, try typing the key phrase in the Continual Learning tab."
        elif score > 0.3:
            emoji = "😐"
            confirmation_prompt = "I'm not fully confident. Please glance over the transcript and correct anything off."
            fallback_message = "You can also re-record or add more context if needed."
        else:
            emoji = "😊"
            confirmation_prompt = "Transcript looks stable. You can proceed or refine details if you like."
            fallback_message = ""
        frustration_display = f"{emoji} Mode: {mode} (frustration score {score:.2f})"

    if temp_path:
        try:
            os.unlink(temp_path)
        except OSError:
            LOGGER.warning("Failed to delete temp audio file %s", temp_path)

    return (
        baseline["transcript"],
        baseline["word_timings"],
        personalized["transcript"],
        personalized["word_timings"],
        repaired,
        comparison,
        similarity_df,
        accuracy_df,
        confidence_df,
        timing_df,
        readability_df,
        grammar_df,
        error_df,
        repair_impact,
        confusion_pairs,
        adv_df,
        interaction,
        frustration_display,
        confirmation_prompt,
        fallback_message,
    )


def submit_correction(user_id: str, audio_path: str, baseline_text: str, personalized_text: str,
                      user_correction: str, context: str):
    user_id = parse_profile_id(user_id)
    if not user_id:
        raise gr.Error("Create or select a profile first.")
    CorrectionManager().add_correction(
        user_id=user_id,
        audio_path=audio_path,
        asr_baseline=baseline_text,
        asr_personalized=personalized_text,
        user_correction=user_correction,
        context=context,
    )
    CorrectionManager().update_vocabulary(user_id)
    PronunciationMapper().update_patterns(user_id, personalized_text, user_correction)
    history = CorrectionManager().get_correction_history(user_id, limit=50)
    history_df = pd.DataFrame(
        [
            {
                "timestamp": h.timestamp,
                "baseline": h.asr_baseline,
                "personalized": h.asr_personalized,
                "correction": h.user_correction,
            }
            for h in history
        ]
    )
    patterns = PronunciationMapper().top_patterns(user_id, limit=50)
    patterns_df = pd.DataFrame(
        [
            {"user_variant": p.user_variant, "standard_form": p.standard_form,
             "confidence": p.confidence, "count": p.occurrence_count}
            for p in patterns
        ]
    )
    return history_df, patterns_df


def refresh_patterns(user_id: str):
    user_id = parse_profile_id(user_id)
    patterns = PronunciationMapper().top_patterns(user_id, limit=50)
    patterns_df = pd.DataFrame(
        [
            {"user_variant": p.user_variant, "standard_form": p.standard_form,
             "confidence": p.confidence, "count": p.occurrence_count}
            for p in patterns
        ]
    )
    return patterns_df


def run_model_comparison(user_id: str, audio_input, uploaded_file, demo_audio_path: str, vocab_text: str,
                         ground_truth: str):
    user_id = parse_profile_id(user_id)
    audio_path = demo_audio_path or None
    temp_path = None
    if not audio_path:
        upload_path = _extract_upload_path(uploaded_file)
        if upload_path:
            audio_path = upload_path
        else:
            audio_path, temp_path = _persist_audio(audio_input)
    if not audio_path:
        raise gr.Error("Please upload/record audio or select a demo file.")
    vocab = parse_custom_vocab(vocab_text)
    comparator = ModelComparator()
    results = asyncio.run(comparator.compare_all_models(audio_path, vocab, ground_truth))
    best = comparator.determine_best_model(results)
    ensemble = comparator.model_ensemble(results)

    df = pd.DataFrame(results)
    best_text = best["model"] if best else "N/A"
    if user_id:
        _record_model_perf(user_id, results)

    if temp_path:
        try:
            os.unlink(temp_path)
        except OSError:
            LOGGER.warning("Failed to delete temp audio file %s", temp_path)

    return df, best_text, ensemble


def load_profiles():
    pm = ProfileManager()
    profiles = pm.list_profiles()
    return [f"{p['user_id']} | {p['name']}" for p in profiles]


def load_profile_vocab_for_dropdown(profile_label: str) -> str:
    """When user selects a profile, load its stored custom_vocabulary into the vocab textbox."""
    user_id = parse_profile_id(profile_label)
    if not user_id:
        return DEFAULT_VOCAB
    profile = ProfileManager().load_profile(user_id)
    if not profile:
        return DEFAULT_VOCAB
    cv = profile.get("custom_vocabulary")
    if not cv:
        return DEFAULT_VOCAB
    if isinstance(cv, str):
        return cv
    if isinstance(cv, list):
        lines = []
        for item in cv:
            if isinstance(item, dict):
                w = item.get("word", "")
                b = item.get("boost", 1.5)
                if w:
                    lines.append(f"{w}:{b}")
            elif isinstance(item, str):
                lines.append(item)
        return "\n".join(lines) if lines else DEFAULT_VOCAB
    return DEFAULT_VOCAB


def create_profile(name: str, characteristics: str):
    pm = ProfileManager()
    user_id = pm.create_profile(name, {"notes": characteristics})
    return load_profiles(), f"{user_id} | {name}"


def parse_profile_id(label: str) -> str:
    if not label:
        return ""
    return label.split("|")[0].strip()


def export_profile(user_label: str):
    user_id = parse_profile_id(user_label)
    if not user_id:
        raise gr.Error("Select a profile.")
    path = os.path.join("profiles", f"{user_id}.json")
    ProfileManager().export_profile(user_id, path)
    return path


def import_profile(file_obj):
    if file_obj is None:
        raise gr.Error("Upload a profile JSON.")
    path = file_obj.name if hasattr(file_obj, "name") else file_obj
    user_id = ProfileManager().import_profile(path)
    return load_profiles(), user_id


def generate_export(format_choice: str, data_json: str):
    manager = ExportManager()
    data = []
    if data_json:
        try:
            data = pd.read_json(data_json).to_dict(orient="records")
        except Exception:
            data = []
    if format_choice == "LaTeX":
        return manager.generate_latex_table(data)
    if format_choice == "JSON":
        return manager.create_research_summary({"generated": True}, {"data": data})
    if format_choice == "CSV":
        path = manager.export_anonymized_dataset(data)
        return path
    return ""


init_db()

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
PATENT_MANIFEST_PATH = os.path.join(REPORTS_DIR, "patent_build_manifest.json")


def _patent_verification_markdown() -> str:
    """Build markdown for Patent/Verification block: three layers + manifest counts if present."""
    lines = [
        "**Three-layer verification (patent-ready):**",
        "",
        "1. **Baseline ASR** — Generic speech-to-text (e.g. Deepgram) without user adaptation.",
        "2. **Personalized ASR** — Same engine with user-specific vocabulary and pronunciation patterns.",
        "3. **Semantic Repair** — LLM-based repair of ASR output for clarity and grammar.",
        "",
        "Verification data is pre-loaded from the patent build. Select an Illinois_&lt;SpeakerID&gt; profile; "
        "Custom Vocabulary auto-fills. Use Built-in Demo Audio or local path to run the pipeline.",
    ]
    try:
        if os.path.isfile(PATENT_MANIFEST_PATH):
            with open(PATENT_MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            lines.append("")
            lines.append("---")
            lines.append("**Pre-loaded verification data:**")
            lines.append("- **Speakers:** %s" % (", ".join(manifest.get("speakers", [])) or "—"))
            lines.append("- **Profiles:** %d (Illinois_&lt;ID&gt;)" % manifest.get("profile_count", 0))
            lines.append("- **Total audio files:** %d" % manifest.get("total_audio_files", 0))
            built = manifest.get("built_at", "")
            if built:
                lines.append("- **Build time:** %s" % built)
    except Exception:
        pass
    return "\n".join(lines)


with gr.Blocks(title="Personal Speech Adaptation Layer - Phase 2") as app:
    gr.Markdown("# Personal Speech Adaptation Layer - Research System")

    with gr.Accordion("Patent / Verification Summary", open=True):
        gr.Markdown(_patent_verification_markdown())

    with gr.Row():
        profile_dropdown = gr.Dropdown(choices=load_profiles(), label="Select Profile")
        new_profile_btn = gr.Button("Create New Profile")

    with gr.Accordion("Settings", open=False):
        enable_learning = gr.Checkbox(label="Enable Continual Learning", value=True)
        enable_multimodel = gr.Checkbox(label="Enable Multi-Model Comparison", value=False)
        enable_adaptive = gr.Checkbox(label="Enable Adaptive Interaction", value=True)

    with gr.Tabs():
        with gr.Tab("Demo"):
            with gr.Row():
                audio_input = gr.Audio(label="Record Audio (Mic)", type="numpy", sources=["microphone"])
                context_input = gr.Textbox(label="Domain Hints (optional)", lines=6)
            uploaded_audio = gr.File(label="Upload Audio File", file_types=[".wav", ".flac", ".mp3", ".m4a"])
            demo_audio = gr.Dropdown(label="Built-in Demo Audio", choices=_list_demo_audio())
            audio_url_input = gr.Textbox(label="Or paste direct audio URL (WAV/MP3/FLAC)", placeholder="https://...", lines=1)
            audio_path_input = gr.Textbox(label="Or full path to local WAV (e.g. D:\\...\\CF03\\file.wav)", placeholder="D:\\research\\data\\UASpeech\\audio\\original\\CF03\\file.wav", lines=1)
            vocab_input = gr.Textbox(label="Custom Vocabulary (word:boost)", lines=6, value=DEFAULT_VOCAB)
            ground_truth_input = gr.Textbox(label="Ground Truth (optional)", lines=4)
            task_context_input = gr.Textbox(label="Task Context for LATTEScore (optional)", lines=2)
            run_btn = gr.Button("Run Pipeline", variant="primary")

            with gr.Row():
                baseline_out = gr.Textbox(label="Baseline ASR Transcript", lines=4)
                personalized_out = gr.Textbox(label="Personalized ASR Transcript", lines=4)
                repaired_out = gr.Textbox(label="Semantic Repair Output", lines=4)

            with gr.Row():
                baseline_words = gr.JSON(label="Baseline Word Timings")
                personalized_words = gr.JSON(label="Personalized Word Timings")

            comparison_table = gr.Dataframe(label="Side-by-Side Comparison", interactive=False, wrap=True)
            similarity_table = gr.Dataframe(label="Similarity Metrics", interactive=False, wrap=True)
            accuracy_table = gr.Dataframe(label="WER/CER vs Ground Truth", interactive=False, wrap=True)
            confidence_table = gr.Dataframe(label="Confidence Metrics", interactive=False, wrap=True)
            timing_table = gr.Dataframe(label="Timing Metrics", interactive=False, wrap=True)
            readability_table = gr.Dataframe(label="Readability Metrics", interactive=False, wrap=True)
            grammar_table = gr.Dataframe(label="Grammar Flags", interactive=False, wrap=True)
            error_table = gr.Dataframe(label="Error Analysis", interactive=False, wrap=True)
            repair_table = gr.Dataframe(label="Repair Impact", interactive=False, wrap=True)
            confusion_json = gr.JSON(label="Top Replacement Pairs")
            adv_table = gr.Dataframe(label="Advanced Metrics", interactive=False, wrap=True)
            interaction_json = gr.JSON(label="Adaptive Interaction State")
            frustration_indicator = gr.Markdown("😊 Mode: INTEGRATION (frustration score 0.00)")
            confirmation_markdown = gr.Markdown("")
            fallback_markdown = gr.Markdown("")

            run_btn.click(
                run_pipeline_phase2,
                inputs=[
                    profile_dropdown,
                    audio_input,
                    uploaded_audio,
                    demo_audio,
                    audio_url_input,
                    audio_path_input,
                    vocab_input,
                    context_input,
                    ground_truth_input,
                    task_context_input,
                    enable_learning,
                    enable_adaptive,
                ],
                outputs=[
                    baseline_out,
                    baseline_words,
                    personalized_out,
                    personalized_words,
                    repaired_out,
                    comparison_table,
                    similarity_table,
                    accuracy_table,
                    confidence_table,
                    timing_table,
                    readability_table,
                    grammar_table,
                    error_table,
                    repair_table,
                    confusion_json,
                    adv_table,
                    interaction_json,
                    frustration_indicator,
                    confirmation_markdown,
                    fallback_markdown,
                ],
            )
            profile_dropdown.change(
                load_profile_vocab_for_dropdown,
                inputs=[profile_dropdown],
                outputs=[vocab_input],
            )

        with gr.Tab("Continual Learning"):
            correction_text = gr.Textbox(label="Correct This Transcript", lines=4)
            correction_context = gr.Textbox(label="Correction Context (optional)", lines=2)
            submit_btn = gr.Button("Submit Correction")
            correction_history = gr.Dataframe(label="Correction History", interactive=False, wrap=True)
            pattern_table = gr.Dataframe(label="Pronunciation Patterns", interactive=False, wrap=True)
            submit_btn.click(
                submit_correction,
                inputs=[profile_dropdown, demo_audio, baseline_out, personalized_out, correction_text, correction_context],
                outputs=[correction_history, pattern_table],
            )

        with gr.Tab("Pronunciation Patterns"):
            refresh_btn = gr.Button("Refresh Patterns")
            patterns_df = gr.Dataframe(label="Detected Patterns", interactive=False, wrap=True)
            refresh_btn.click(refresh_patterns, inputs=[profile_dropdown], outputs=[patterns_df])

        with gr.Tab("Model Comparison"):
            compare_btn = gr.Button("Run Model Comparison")
            model_df = gr.Dataframe(label="Model Outputs", interactive=False, wrap=True)
            best_model = gr.Textbox(label="Recommended Model")
            ensemble_out = gr.Textbox(label="Ensemble Output", lines=4)
            compare_btn.click(
                run_model_comparison,
                inputs=[profile_dropdown, audio_input, uploaded_audio, demo_audio, vocab_input, ground_truth_input],
                outputs=[model_df, best_model, ensemble_out],
            )

        with gr.Tab("Analytics"):
            analytics = AnalyticsDashboard()
            chart_wer = gr.Plot(label="WER Over Time")
            chart_sem = gr.Plot(label="SemScore Over Time")
            chart_task = gr.Plot(label="Task Success Rate")
            refresh_analytics = gr.Button("Refresh Analytics")
            thesis_btn = gr.Button("Generate Thesis Export")
            thesis_output = gr.Textbox(label="Thesis Export Directory", lines=2)

            def _refresh(user_label: str):
                user_id = parse_profile_id(user_label)
                return analytics.performance_over_time(user_id)

            def _generate_thesis(user_label: str):
                if ThesisGenerator is None:
                    return "Thesis export unavailable. Install: pip install scipy matplotlib numpy"
                user_id = parse_profile_id(user_label)
                generator = ThesisGenerator()
                out_dir = generator.generate_results_chapter_for_user(user_id or None)
                return out_dir

            refresh_analytics.click(
                _refresh,
                inputs=[profile_dropdown],
                outputs=[chart_wer, chart_sem, chart_task],
            )
            thesis_btn.click(
                _generate_thesis,
                inputs=[profile_dropdown],
                outputs=[thesis_output],
            )

        with gr.Tab("Profile Management"):
            profile_name = gr.Textbox(label="Name")
            profile_characteristics = gr.Textbox(label="Speech Characteristics", lines=2)
            create_btn = gr.Button("Create Profile")
            export_btn = gr.Button("Export Profile")
            import_file = gr.File(label="Import Profile JSON")
            export_path = gr.Textbox(label="Export Path")

            create_btn.click(create_profile, inputs=[profile_name, profile_characteristics],
                             outputs=[profile_dropdown, profile_dropdown])
            export_btn.click(export_profile, inputs=[profile_dropdown], outputs=[export_path])
            import_file.change(import_profile, inputs=[import_file], outputs=[profile_dropdown, profile_dropdown])

        with gr.Tab("Export"):
            format_choice = gr.Dropdown(choices=["LaTeX", "CSV", "JSON"], label="Format")
            data_json = gr.Textbox(label="Data JSON (from analytics)", lines=6)
            export_btn2 = gr.Button("Generate Export")
            export_output = gr.Textbox(label="Export Output / Path", lines=4)
            export_btn2.click(generate_export, inputs=[format_choice, data_json], outputs=[export_output])


if __name__ == "__main__":
    _allowed = [SAMPLE_AUDIO_DIR, tempfile.gettempdir()]
    _ext = os.environ.get("UASPEECH_AUDIO_DIR", "").strip()
    if _ext and os.path.isdir(_ext):
        _allowed.append(_ext)
    app.launch(allowed_paths=_allowed)
