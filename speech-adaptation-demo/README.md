# Personal Speech Adaptation Layer Demo

This Gradio app demonstrates a 4-stage speech processing pipeline:
1. Baseline ASR (no customization)
2. Personalized ASR with keyword boosting
3. LLM semantic repair
4. Side-by-side comparison table

## Requirements
- Python 3.9+
- Deepgram API key
- OpenAI API key

## Setup
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Add keys to `.env`:
   ```
   DEEPGRAM_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ```

## Run
```bash
python app.py
```

## Phase 2 (Research System)
Phase 2 adds profiles, continual learning, pronunciation patterns, multi-model comparison,
advanced metrics, analytics dashboards, and publication-ready exports.

### Run Phase 2
```bash
python app_phase2.py
```

### Extra Environment Variables
- `GOOGLE_APPLICATION_CREDENTIALS` (optional) for Google STT

### Phase 2 Data
- SQLite DB: `speech-adaptation-demo/profiles/user_profiles.db`
- Exports: `speech-adaptation-demo/exports/`

### Tests
```bash
python -m pytest tests/phase2_tests.py
```

## Notes
- Supported audio formats: WAV, MP3, FLAC, M4A.
- The default custom vocabulary includes example medical and proper-noun terms.
- Use the "Domain Hints" box to provide context for semantic repair.
- If M4A/MP3 decoding fails, install FFmpeg so `pydub` can convert those files.
