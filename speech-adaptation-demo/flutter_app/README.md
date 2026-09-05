# Speech Adaptation – Simple Flutter App

Simple, easy-to-understand frontend for the Speech Adaptation pipeline (Baseline → Personalized → Repaired). Uses the same backend as the Gradio app via the REST API.

## Prerequisites

- Flutter SDK: https://docs.flutter.dev/get-started/install
- Backend running: from `speech-adaptation-demo` run `python api_server.py` (port 8000)

## Run

```bash
# From this directory (speech-adaptation-demo/flutter_app)
flutter pub get
flutter run
```

- **Chrome:** `flutter run -d chrome`
- **Windows:** `flutter run -d windows`
- **Android emulator:** Change `kBaseUrl` in `lib/api/client.dart` to `http://10.0.2.2:8000`

## Screens

1. **Home** – Short explanation of the three layers + data summary (if patent build was run). One button: "Start – Run pipeline".
2. **Run** – Pick profile (dropdown), pick audio (dropdown from demo list), optional ground truth and context. One button: "Run pipeline".
3. **Results** – Three cards: Baseline, Personalized, Repaired transcripts; one line for WER if ground truth was provided.

No extra toggles or advanced tables on the main path. For full metrics and research features, use the Gradio app (`python app_phase2.py`).
