import os
from datetime import datetime
from typing import Tuple

import gradio as gr
import pandas as pd
import soundfile as sf
from dotenv import load_dotenv

from analytics import wer
from asr_processor import baseline_asr, personalized_asr
from semantic_repair import semantic_repair
from phase2.db import StudyTaskAttempt, get_session, init_db


STUDY_TASKS = [
    {"number": 1, "name": "Turn on the lights", "prompt": "Say: 'Turn on the lights'"},
    {
        "number": 2,
        "name": "Medication timing",
        "prompt": "Say: 'What time should I take my medication?'",
    },
    {
        "number": 3,
        "name": "Schedule appointment",
        "prompt": "Say: 'Schedule an appointment for Tuesday'",
    },
    {
        "number": 4,
        "name": "Weather",
        "prompt": "Say: 'What's the weather tomorrow?'",
    },
    {
        "number": 5,
        "name": "Call doctor",
        "prompt": "Say: 'Call my doctor'",
    },
]


def _ensure_env() -> None:
    load_dotenv()
    missing = []
    if not os.getenv("DEEPGRAM_API_KEY"):
        missing.append("DEEPGRAM_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if missing:
        raise gr.Error(f"Missing API keys in .env: {', '.join(missing)}")


def _persist_audio(audio_input) -> Tuple[str | None, str | None]:
    if audio_input is None:
        return None, None
    if isinstance(audio_input, str):
        return audio_input, None
    if isinstance(audio_input, (list, tuple)) and len(audio_input) == 2:
        sample_rate, data = audio_input
        tmp = sf.SoundFile
        # Save to temporary WAV file
        import tempfile

        tmp_file = tempfile.NamedTemporaryFile(
            prefix="study_audio_", suffix=".wav", delete=False
        )
        path = tmp_file.name
        tmp_file.close()
        sf.write(path, data, sample_rate)
        return path, path
    return None, None


def _current_task(task_index: int) -> dict:
    idx = max(0, min(task_index, len(STUDY_TASKS) - 1))
    return STUDY_TASKS[idx]


def run_study_task(
    participant_id: str,
    condition: str,
    task_index: int,
    audio_input,
    user_correction: str,
):
    _ensure_env()
    if not participant_id:
        raise gr.Error("Please enter a Participant ID to continue.")

    task = _current_task(task_index)
    audio_path, temp_path = _persist_audio(audio_input)
    if not audio_path:
        raise gr.Error("Please record audio for this task.")

    # Core 3-stage pipeline (no custom vocab for simplicity)
    baseline = baseline_asr(audio_path)
    personalized = personalized_asr(audio_path, [])
    repaired = semantic_repair(personalized["transcript"], "")

    # Optional simple WER against participant correction if provided
    baseline_wer = personalized_wer = repaired_wer = None
    if user_correction and user_correction.strip():
        ref = user_correction.strip()
        baseline_wer = wer(ref, baseline["transcript"]) or 0.0
        personalized_wer = wer(ref, personalized["transcript"]) or 0.0
        repaired_wer = wer(ref, repaired) or 0.0

    # Persist attempt
    db = get_session()
    try:
        attempt = StudyTaskAttempt(
            participant_id=participant_id,
            task_number=task["number"],
            task_name=task["name"],
            audio_path=audio_path,
            baseline_output=baseline["transcript"],
            personalized_output=personalized["transcript"],
            repaired_output=repaired,
            user_correction=user_correction or "",
            timestamp=datetime.utcnow(),
        )
        db.add(attempt)
        db.commit()
    finally:
        db.close()

    if temp_path:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    progress = f"Task {task['number']} of {len(STUDY_TASKS)}"
    return (
        baseline["transcript"],
        personalized["transcript"],
        repaired,
        baseline_wer,
        personalized_wer,
        repaired_wer,
        progress,
    )


def export_study_results_csv() -> str:
    """
    Export all study task attempts to a single CSV file.
    """
    db = get_session()
    try:
        attempts = db.query(StudyTaskAttempt).order_by(StudyTaskAttempt.timestamp.asc()).all()
    finally:
        db.close()

    rows = []
    for a in attempts:
        rows.append(
            {
                "participant_id": a.participant_id,
                "task_number": a.task_number,
                "task_name": a.task_name,
                "audio_path": a.audio_path,
                "baseline_output": a.baseline_output,
                "personalized_output": a.personalized_output,
                "repaired_output": a.repaired_output,
                "user_correction": a.user_correction,
                "timestamp": a.timestamp.isoformat() if a.timestamp else "",
            }
        )
    df = pd.DataFrame(rows)
    exports_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(exports_dir, exist_ok=True)
    path = os.path.join(
        exports_dir,
        f"study_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
    )
    df.to_csv(path, index=False)
    return path


init_db()

with gr.Blocks(title="Speech Study - Simple Interface") as app:
    gr.Markdown("# Speech Study Demo - Participant Interface")

    with gr.Tab("Consent & Demographics"):
        gr.Markdown(
            "Please read the consent information provided by the researcher. "
            "By checking the box below you indicate that you consent to participate."
        )
        consent_check = gr.Checkbox(label="I consent to participate in this study")
        participant_id = gr.Textbox(label="Participant ID (e.g., P001)")
        condition = gr.Dropdown(
            label="Speech condition",
            choices=["None", "Mild", "Moderate", "Severe"],
            value="None",
        )
        start_button = gr.Button("Start Study", variant="primary")

    with gr.Tab("Tasks") as task_tab:
        task_tab.visible = False
        task_prompt = gr.Markdown("Task instructions will appear here.")
        audio_input = gr.Audio(
            label="Record Audio", type="numpy", sources=["microphone"]
        )
        correction_box = gr.Textbox(
            label="If the transcript is wrong, type the correct version (optional)",
            lines=2,
        )
        submit_button = gr.Button("Submit Recording", variant="primary")

        with gr.Row():
            baseline_out = gr.Textbox(label="Baseline Transcript", lines=3)
            personalized_out = gr.Textbox(label="Personalized Transcript", lines=3)
            repaired_out = gr.Textbox(label="Repaired Transcript", lines=3)

        with gr.Row():
            baseline_wer_out = gr.Number(label="Baseline WER (if reference provided)", precision=4)
            personalized_wer_out = gr.Number(
                label="Personalized WER (if reference provided)", precision=4
            )
            repaired_wer_out = gr.Number(
                label="Repaired WER (if reference provided)", precision=4
            )

        progress_label = gr.Markdown("Task 1 of 5")
        next_button = gr.Button("Next Task")
        hidden_task_index = gr.State(0)

    with gr.Tab("Progress"):
        gr.Markdown("Study progress and exports.")
        export_button = gr.Button("Export Results CSV")
        export_path_box = gr.Textbox(label="Results CSV Path", lines=2)

    def _start_study(consent: bool, pid: str, cond: str):
        if not consent:
            raise gr.Error("You must consent to participate before continuing.")
        if not pid:
            raise gr.Error("Please enter a Participant ID.")
        first_task = _current_task(0)
        return (
            gr.update(visible=True),
            first_task["prompt"],
            0,
            "Task 1 of {}".format(len(STUDY_TASKS)),
        )

    start_button.click(
        _start_study,
        inputs=[consent_check, participant_id, condition],
        outputs=[task_tab, task_prompt, hidden_task_index, progress_label],
    )

    def _on_submit(pid: str, cond: str, idx: int, audio, correction: str):
        return run_study_task(pid, cond, idx, audio, correction)

    submit_button.click(
        _on_submit,
        inputs=[participant_id, condition, hidden_task_index, audio_input, correction_box],
        outputs=[
            baseline_out,
            personalized_out,
            repaired_out,
            baseline_wer_out,
            personalized_wer_out,
            repaired_wer_out,
            progress_label,
        ],
    )

    def _next(idx: int):
        new_idx = min(idx + 1, len(STUDY_TASKS) - 1)
        task = _current_task(new_idx)
        return new_idx, task["prompt"], f"Task {task['number']} of {len(STUDY_TASKS)}"

    next_button.click(
        _next,
        inputs=[hidden_task_index],
        outputs=[hidden_task_index, task_prompt, progress_label],
    )

    export_button.click(
        export_study_results_csv, inputs=None, outputs=[export_path_box]
    )


if __name__ == "__main__":
    app.launch()

