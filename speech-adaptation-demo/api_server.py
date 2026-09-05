"""
REST API for the Speech Adaptation pipeline. Use this backend with a Flutter (or any) frontend.

Run: python api_server.py
Then open http://localhost:8000/docs for Swagger UI.

Endpoints:
  GET  /api/health           - Health check
  GET  /api/profiles         - List profiles (id, label, name)
  GET  /api/profiles/{id}/vocabulary - Vocabulary text for profile
  GET  /api/demo-audio       - List of demo audio paths/labels
  GET  /api/patent-summary   - Manifest counts if available
  POST /api/pipeline/run     - Run pipeline (multipart: profile_id, audio file or demo_audio_path, optional ground_truth, context_hints)
"""

import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Add project to path and init DB before importing app_phase2
DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
if DEMO_DIR not in __import__("sys").path:
    __import__("sys").path.insert(0, DEMO_DIR)
os.chdir(DEMO_DIR)

from phase2 import init_db

init_db()


def _list_demo_audio():
    sample_audio_dir = os.path.join(DEMO_DIR, "sample_audio")
    ext = {".wav", ".mp3", ".flac", ".m4a"}
    files = []
    if os.path.isdir(sample_audio_dir):
        for name in sorted(os.listdir(sample_audio_dir)):
            if name.startswith("."):
                continue
            path = os.path.join(sample_audio_dir, name)
            if os.path.isfile(path) and os.path.splitext(name)[1].lower() in ext:
                files.append({"path": path, "label": name})
            elif os.path.isdir(path):
                for sub in sorted(os.listdir(path)):
                    if sub.startswith("."):
                        continue
                    if os.path.splitext(sub)[1].lower() in ext:
                        full = os.path.join(path, sub)
                        files.append({"path": full, "label": f"{name} / {sub}"})
    external = os.environ.get("UASPEECH_AUDIO_DIR", "").strip()
    if external and os.path.isdir(external):
        for name in sorted(os.listdir(external)):
            if name.startswith("."):
                continue
            path = os.path.join(external, name)
            if os.path.isfile(path) and os.path.splitext(name)[1].lower() in ext:
                files.append({"path": path, "label": f"[External] {name}"})
            elif os.path.isdir(path):
                for sub in sorted(os.listdir(path)):
                    if sub.startswith("."):
                        continue
                    if os.path.splitext(sub)[1].lower() in ext:
                        full = os.path.join(path, sub)
                        files.append({"path": full, "label": f"[External] {name} / {sub}"})
    return files


def _get_profile_label(user_id: str) -> str:
    from phase2.profile_manager import ProfileManager
    pm = ProfileManager()
    for p in pm.list_profiles():
        if p["user_id"] == user_id:
            return f"{p['user_id']} | {p['name']}"
    return ""


def _vocab_for_profile(user_id: str) -> str:
    from app_phase2 import load_profile_vocab_for_dropdown
    label = _get_profile_label(user_id)
    if not label:
        return ""
    return load_profile_vocab_for_dropdown(label)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Speech Adaptation API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/profiles")
def list_profiles():
    from phase2.profile_manager import ProfileManager
    pm = ProfileManager()
    profiles = pm.list_profiles()
    return [
        {"id": p["user_id"], "label": f"{p['user_id']} | {p['name']}", "name": p["name"]}
        for p in profiles
    ]


@app.get("/api/profiles/{user_id}/vocabulary")
def get_profile_vocabulary(user_id: str):
    text = _vocab_for_profile(user_id)
    if not text and not _get_profile_label(user_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"user_id": user_id, "vocabulary": text}


@app.get("/api/demo-audio")
def list_demo_audio():
    return _list_demo_audio()


@app.get("/api/patent-summary")
def patent_summary():
    import json
    path = os.path.join(DEMO_DIR, "reports", "patent_build_manifest.json")
    if not os.path.isfile(path):
        return {"present": False}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"present": True, **data}
    except Exception:
        return {"present": False}


def _df_to_records(df):
    if df is None or (hasattr(df, "empty") and df.empty):
        return []
    return df.to_dict(orient="records")


@app.post("/api/pipeline/run")
async def run_pipeline(
    profile_id: str = Form(..., description="Profile user_id (e.g. user_abc123 or from GET /api/profiles)"),
    ground_truth: str = Form(""),
    context_hints: str = Form(""),
    demo_audio_path: str = Form("", description="One of the paths from GET /api/demo-audio"),
    audio: UploadFile = File(None),
):
    from app_phase2 import run_pipeline_phase2

    profile_label = _get_profile_label(profile_id)
    if not profile_label:
        raise HTTPException(status_code=400, detail="Profile not found")
    vocab_text = _vocab_for_profile(profile_id)
    audio_path = None
    temp_path = None
    if demo_audio_path and os.path.isfile(demo_audio_path):
        audio_path = demo_audio_path
    if not audio_path and audio and audio.filename:
        suffix = os.path.splitext(audio.filename)[1] or ".wav"
        if suffix.lower() not in {".wav", ".mp3", ".flac", ".m4a"}:
            suffix = ".wav"
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="api_audio_")
        os.close(fd)
        try:
            content = await audio.read()
            with open(temp_path, "wb") as f:
                f.write(content)
            audio_path = temp_path
        except Exception as e:
            if temp_path and os.path.isfile(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise HTTPException(status_code=400, detail=f"Failed to save audio: {e}")
    if not audio_path:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'audio' file upload or 'demo_audio_path' from GET /api/demo-audio",
        )
    try:
        result = run_pipeline_phase2(
            profile_label,
            None,
            None,
            audio_path,
            "",
            "",
            vocab_text,
            context_hints or "",
            ground_truth or "",
            "",
            True,
            True,
        )
    except Exception as e:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        msg = str(e)
        if "Please upload" in msg or "select" in msg.lower():
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
    if temp_path and os.path.isfile(temp_path):
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    (
        baseline_transcript,
        baseline_words,
        personalized_transcript,
        personalized_words,
        repaired,
        comparison_df,
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
    ) = result

    return {
        "baseline_transcript": baseline_transcript,
        "personalized_transcript": personalized_transcript,
        "repaired_transcript": repaired,
        "accuracy": _df_to_records(accuracy_df),
        "comparison": _df_to_records(comparison_df),
        "similarity": _df_to_records(similarity_df),
        "confidence": _df_to_records(confidence_df),
        "timing": _df_to_records(timing_df),
        "readability": _df_to_records(readability_df),
        "grammar": _df_to_records(grammar_df),
        "error_analysis": _df_to_records(error_df),
        "repair_impact": _df_to_records(repair_impact),
        "confusion_pairs": confusion_pairs,
        "advanced_metrics": _df_to_records(adv_df),
        "frustration_display": frustration_display,
        "confirmation_prompt": confirmation_prompt,
        "fallback_message": fallback_message,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
