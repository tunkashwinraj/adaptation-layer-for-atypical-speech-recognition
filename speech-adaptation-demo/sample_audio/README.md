# Demo Audio for Speech Adaptation

Put audio files here (WAV, MP3, FLAC, or M4A). They will appear in the **Built-in Demo Audio** dropdown when you run `app.py` or `app_phase2.py`.

## Quick ways to get test data

### Option 1: Use the app’s “Audio URL” box (no download)

In **app.py** and **app_phase2.py** you can paste a **direct link** to an audio file (WAV or MP3). The app will fetch it and run the pipeline. Use any public URL that points **directly** to the file (e.g. “Open in new tab” → copy that URL). Examples:

- A **Google Drive** or **Dropbox** direct-download link (e.g. `https://drive.google.com/uc?export=download&id=...` for Drive).
- A direct link from a dataset (e.g. raw file URL from GitHub or a dataset host).
- Any `https://...` URL that returns audio (WAV/MP3/FLAC) when opened in a browser.

### Option 2: Download and put files in this folder

1. **Create the folder** (it’s already there if you see this README).
2. **Download** one of the sources below (or your own data).
3. **Copy** WAV/MP3/FLAC/M4A files into `sample_audio/`.
4. **Restart** the app; they will show up in **Built-in Demo Audio**.

---

## Recommended data sources

### For general English ASR testing (clean speech)

| Source | What it is | Link | How to get a few files |
|--------|------------|------|-------------------------|
| **LibriSpeech** | Read English, 16 kHz, with transcripts | https://www.openslr.org/12 | Download **dev-clean** (337 MB) or **test-clean** (346 MB). Unzip; inside you’ll find `.flac` files and `.txt` transcripts. Copy a few `.flac` files into `sample_audio/`. Use the matching `.txt` as **Ground Truth** in the app. |
| **Mozilla Common Voice** | Crowdsourced English, multiple accents | https://commonvoice.mozilla.org/en/datasets | Download the English dataset (large). Unzip and copy some MP3s from the `clips/` folder into `sample_audio/`. Use the dataset’s TSV for transcripts as Ground Truth. |

### For atypical / dysarthric speech (closest to your thesis)

| Source | What it is | How to get it |
|--------|------------|----------------|
| **UA-Speech** | Dysarthric (cerebral palsy) isolated words | E-mail **uaspeech-requests@lists.illinois.edu** with your name, institution, intended use, and delivery account (Google/iCloud/OneDrive). Put received WAVs in `sample_audio/` and use the provided word list as Ground Truth. |
| **TORGO** | Dysarthric continuous speech (ALS/CP) | Licensed via LDC: https://catalog.ldc.upenn.edu/LDC2012S02 (LDC membership required). After obtaining, copy WAVs into `sample_audio/` and use the included transcripts as Ground Truth. |

### Direct download links (LibriSpeech)

- **dev-clean** (smaller, good for testing):  
  https://www.openslr.org/resources/12/dev-clean.tar.gz  
- **test-clean**:  
  https://www.openslr.org/resources/12/test-clean.tar.gz  

After downloading, extract and copy a few `.flac` files (and their `.txt` transcripts) into this folder.

---

## File naming

- Use **only** files with extensions: `.wav`, `.mp3`, `.flac`, `.m4a`.
- You can keep transcripts in a separate `.txt` or paste them into the app’s **Ground Truth** box when you run the pipeline.

## Testing flow

1. **Phase 1 (app.py):** Choose a file from **Built-in Demo Audio** (or paste an **Audio URL**), add optional Custom Vocabulary and Ground Truth, then click **Run**.
2. **Phase 2 (app_phase2.py):** Same in the Demo tab; use a profile and optional Ground Truth. Use **Model Comparison** and **Analytics** with the same files.
3. **Phase 3 (app_study_simple.py):** Use the mic or upload in the Tasks tab; for repeatable tests you can also add sample files and point the study app at them if you extend the UI.
