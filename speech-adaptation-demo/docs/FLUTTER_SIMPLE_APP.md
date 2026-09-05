# Simple Flutter App + API Guide

The current Gradio UI is powerful but dense. This doc describes a **simpler, stronger** experience built in **Flutter** that talks to the same backend via a **REST API**. Flutter gives you one codebase for **mobile (iOS/Android), web, and desktop (Windows/macOS)** with a clean, easy-to-understand UI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Flutter app (simple UI)                                         │
│  • Pick profile → Pick/record audio → Run → See 3 results        │
│  • Optional: Corrections, Analytics summary                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (REST)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python API (FastAPI)  ←  Run: python api_server.py              │
│  • GET /api/profiles, /api/demo-audio, /api/patent-summary       │
│  • POST /api/pipeline/run (audio file or demo_audio_path)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Same pipeline as Gradio: Baseline ASR → Personalized → Repair    │
│  SQLite, profiles, corrections, analytics                        │
└─────────────────────────────────────────────────────────────────┘
```

- **Backend:** Already implemented in `speech-adaptation-demo/api_server.py`. Run it with `python api_server.py` (port 8000). No Gradio needed for the API.
- **Frontend:** Build a Flutter app that calls these endpoints. Below: simple screens and API contract.

---

## API Contract (for Flutter)

**Base URL:** `http://localhost:8000` (or your server, e.g. `https://your-api.com`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check. Returns `{ "status": "ok" }`. |
| GET | `/api/profiles` | List profiles. Returns `[{ "id", "label", "name" }, ...]`. |
| GET | `/api/profiles/{user_id}/vocabulary` | Vocabulary text for profile. Returns `{ "user_id", "vocabulary" }`. |
| GET | `/api/demo-audio` | List demo audio. Returns `[{ "path", "label" }, ...]`. |
| GET | `/api/patent-summary` | If patent build was run: `{ "present": true, "speakers", "profile_count", "total_audio_files" }`. |
| POST | `/api/pipeline/run` | Run pipeline. **Form/multipart:** `profile_id` (required), `ground_truth`, `context_hints`, `demo_audio_path` (optional), `audio` (optional file). Returns JSON with `baseline_transcript`, `personalized_transcript`, `repaired_transcript`, `accuracy`, `comparison`, etc. |

**CORS:** The API allows all origins so Flutter web/desktop can call it.

**Example (run pipeline with demo audio):**

```http
POST /api/pipeline/run
Content-Type: multipart/form-data

profile_id=user_abc123
demo_audio_path=C:\...\sample_audio\uaspeech_CF03\file.wav
ground_truth=hello
context_hints=
```

**Example (run pipeline with uploaded file):**

```http
POST /api/pipeline/run
Content-Type: multipart/form-data

profile_id=user_abc123
audio=<binary file>
ground_truth=
```

---

## Simple Flutter UI (easy to understand)

Keep the flow to **3–4 screens** so it stays strong and simple.

### 1. Home / Summary

- **One short line:** “Speech Adaptation: Baseline → Personalized → Repaired.”
- If `GET /api/patent-summary` has `present: true`, show: “**X** speakers, **Y** profiles, **Z** audio files loaded.”
- **One big button:** “Start” or “Run pipeline” → goes to **Run** screen.
- Optional small links: “Profiles”, “How it works”.

### 2. Run pipeline (main screen)

- **Step 1 – Profile:** Dropdown or list of profiles from `GET /api/profiles`. Label shows **name** (e.g. “Illinois_CF03”). Value = `id` for API. No vocabulary box here (backend uses it automatically).
- **Step 2 – Audio:**  
  - Option A: Dropdown of demo audio from `GET /api/demo-audio` (show `label`, send `path` as `demo_audio_path`).  
  - Option B: “Upload file” → pick file → send as `audio` in `POST /api/pipeline/run`.  
  - Option C (mobile): “Record” → save to file → send as `audio`.
- **Step 3 (optional):** Small text fields: “Ground truth (what was said)” and “Context hints”.
- **One big button:** “Run pipeline”. On tap: show loading → call `POST /api/pipeline/run` → go to **Results**.

So: **Pick profile → Pick or upload/record audio → (optional) ground truth → Run.** No extra toggles or tables on this screen.

### 3. Results (simple and clear)

- **Three cards (or three sections):**
  - **Baseline:** “Generic ASR” → show `baseline_transcript`.
  - **Personalized:** “With your vocabulary” → show `personalized_transcript`.
  - **Repaired:** “Final (cleaned up)” → show `repaired_transcript`.
- **One main number:** If `accuracy` from the API has WER for each stage, show e.g. “Word error rate: Baseline **X**% → Personalized **Y**% → Repaired **Z**%” so improvement is obvious.
- **One line from API:** Show `confirmation_prompt` or `frustration_display` if you want (e.g. “Transcript looks stable”).
- **Secondary (collapsed or “See more”):** Link or expandable section for full `comparison`, `similarity`, `advanced_metrics` for users who care.

So the user sees **three transcripts and one clear “improvement” metric**, not 10 tables at once.

### 4. Optional: Corrections

- After results, optional button: “Something wrong? Submit correction.”
- Two fields: “What the system said” (pre-filled from personalized or repaired) and “Correct text”.
- On submit: call a **future** endpoint (e.g. `POST /api/corrections`) or keep this for a later phase. For now you can hide this or show “Coming soon”.

### 5. Optional: Analytics summary

- One screen or bottom section: “Your progress.”
- Call a **future** endpoint like `GET /api/analytics/summary?profile_id=...` returning e.g. last 10 runs, average WER, or a simple chart data. Keep it one chart or one table so it stays simple.

---

## What to build in Flutter (order)

1. **Config:** Base URL (e.g. `http://10.0.2.2:8000` for Android emulator, `http://localhost:8000` for web/desktop).
2. **HTTP client:** Use `dio` or `http`; add a small API client class that calls the endpoints above.
3. **Screens:**  
   - Home (summary + “Start”).  
   - Run (profile dropdown, audio dropdown or file picker / recorder, optional ground truth, “Run” button).  
   - Results (three transcripts + one WER summary + optional “See more”).
4. **State:** Keep it simple (e.g. one “run state” object: selected profile, selected audio path or file, result JSON, loading/error).
5. **Errors:** Show API error message (e.g. 400 “Provide audio or demo_audio_path”) in a snackbar or small banner.

No need to replicate every Gradio tab. The goal is **simpler and easier to understand**: one main path (profile → audio → run → three results + one metric).

---

## Flutter project setup

1. Install Flutter: https://docs.flutter.dev/get-started/install  
2. Create a new app next to the backend (or inside the repo):

   ```bash
   cd speech-adaptation-demo
   flutter create flutter_app
   cd flutter_app
   ```

3. Add dependency in `pubspec.yaml`:

   ```yaml
   dependencies:
     flutter:
       sdk: flutter
     http: ^1.2.0
     # or dio: ^5.4.0  (if you prefer dio for multipart)
   ```

4. Implement:
   - A single **API client** (e.g. `lib/api/client.dart`) that calls `GET /api/profiles`, `GET /api/demo-audio`, `GET /api/patent-summary`, `POST /api/pipeline/run` (with `MultipartRequest` if using `http` for file upload).
   - **Screens:** `home_screen.dart`, `run_screen.dart`, `results_screen.dart`.
   - **Models:** Simple classes or maps for profile, demo audio item, pipeline response.

5. Run backend and app:

   ```bash
   # Terminal 1 (from speech-adaptation-demo)
   python api_server.py

   # Terminal 2 (from speech-adaptation-demo/flutter_app)
   flutter run -d chrome
   # or: flutter run -d windows
   # or: flutter run   # for connected device/emulator
   ```

---

## Summary

- **Backend:** Use `api_server.py`; no need to change the Gradio app. Same pipeline, same data.
- **Flutter:** Build a **simple** flow: Home → Run (profile + audio + optional ground truth) → Results (three transcripts + one main metric). Hide advanced details behind “See more” or later screens.
- This makes the product **stronger** (one clear path), **simpler** (fewer fields), and **easier to understand** (three layers + one number), and you can still ship the full Gradio app for power users or research.
