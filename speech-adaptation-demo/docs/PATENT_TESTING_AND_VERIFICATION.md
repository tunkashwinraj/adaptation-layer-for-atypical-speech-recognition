# Patent Filing – Testing and Verification

This document describes how to run **code-level tests**, use the **dashboard** with UA-Speech data, and produce **verification reports** suitable for patent and thesis.

---

## 0. One-command patent-ready full build (recommended)

Run **once** from `speech-adaptation-demo`; no other commands needed. Then launch the app to see multiple speakers, many audio files, and full verification data.

```powershell
cd speech-adaptation-demo
python scripts/patent_ready_full_build.py
```

Optional arguments:

- `--uaspeech_root "D:\research\data\UASpeech"` (default)
- `--copy_max 150` — WAVs to copy per speaker (default 150)
- `--speakers "CF03,M16"` — limit to these speakers, or omit for **all** speakers
- `--seed_sessions 5` — run pipeline on 5 files per speaker so Analytics/Export have data (0 to skip; requires API keys)
- `--skip_pseudo` — skip building pseudo-sentences

After the build:

- **Manifest:** `reports/patent_build_manifest.json` (speakers, profile count, total audio files)
- **Summary:** `reports/PATENT_READY_SUMMARY.txt`
- **App:** Open **Patent / Verification Summary** at the top to see the three layers and pre-loaded data counts. Select any **Illinois_&lt;ID&gt;** profile; Custom Vocabulary auto-fills. Use Built-in Demo Audio or local path and **Run Pipeline**.

---

## 1. UA-Speech data layout (Illinois)

- **Root:** `D:\research\data\UASpeech`
- **Audio:** `audio\original\<SpeakerID>\*.wav` (e.g. `audio\original\CF03\CF03_B1_C10_M3.wav`)
- **MLF (ground truth):** `mlf\<SpeakerID>\*_word.mlf` maps filename → word

The setup script now looks for WAVs in **speaker subfolders** (`audio/original/CF03/`) as well as flat `audio/original/`.

---

## 2. One-time setup (run once)

From `speech-adaptation-demo`:

```powershell
# 1) Parse MLF, build vocab, copy WAVs, build pseudo-sentences
python scripts/uaspeech_setup.py --uaspeech_root "D:\research\data\UASpeech" --sample_audio_dir "sample_audio" --speakers "CF03,M16" --copy_max 30

# 2) Create profiles with pre-filled vocabulary (so selecting a profile auto-fills Custom Vocabulary)
python scripts/create_uaspeech_profiles.py --speakers CF03
```

After this:
- **Built-in Demo Audio** lists files under `sample_audio/uaspeech_CF03/` and `sample_audio/uaspeech_CF03_pseudo_sentences/`.
- Profile **Illinois_CF03** exists; selecting it fills **Custom Vocabulary** with 449 words.

---

## 3. Code-level verification tests (automated report)

Runs the 3-stage pipeline on N files and writes a Markdown report to `reports/`.

```powershell
cd speech-adaptation-demo
python scripts/run_verification_tests.py --uaspeech_root "D:\research\data\UASpeech" --speaker CF03 --max_files 10
```

- Requires `.env` with `DEEPGRAM_API_KEY` and `OPENAI_API_KEY`.
- Output: `reports/verification_report_CF03_YYYYMMDD_HHMMSS.md` with per-file WER (Baseline, Personalized, Repaired) and sample transcripts.
- Use this for **patent evidence**: automated, reproducible pipeline run with a fixed dataset.

---

## 4. Dashboard: making the button and audio selection reliable

**If "Run Pipeline" or another button doesn’t respond:**

1. **Provide audio in one of these ways:**
   - **Built-in Demo Audio:** Pick a file from the dropdown (after setup, you’ll see `sample_audio/uaspeech_CF03/...` and pseudo-sentences).
   - **Full path to local WAV:** In **"Or full path to local WAV"**, paste a path, e.g.  
     `D:\research\data\UASpeech\audio\original\CF03\CF03_B1_C10_M3.wav`  
     (No need to use the dropdown.)
   - **Upload:** Use **Upload Audio File**.
   - **URL:** Use **Or paste direct audio URL**.
   - **Mic:** Use **Record Audio (Mic)**.

2. **Allow app to read from D:\\ (optional):**  
   Before starting the app, set:
   ```powershell
   $env:UASPEECH_AUDIO_DIR = "D:\research\data\UASpeech\audio\original"
   python app_phase2.py
   ```
   Then **Built-in Demo Audio** will also list WAVs from that path, and the app is allowed to serve those files.

3. **Profile and vocabulary:**  
   Select **Illinois_CF03** (or another profile). The **Custom Vocabulary** box should auto-fill. If it doesn’t, paste the contents of `sample_audio/uaspeech_setup/uaspeech_CF03_vocab.txt` manually.

4. **Ground Truth:**  
   For a chosen WAV, look up the word in `sample_audio/uaspeech_setup/uaspeech_CF03_basename_to_word.txt` (filename in first column, word in second) and paste it into **Ground Truth**.

5. Click **Run Pipeline**. Then use **Continual Learning** to submit corrections; **Analytics** and **Generate Thesis Export** for tables and figures.

---

## 5. Suggested flow for patent / verification

| Step | Action |
|------|--------|
| 0 (simplest) | Run **one command:** `python scripts/patent_ready_full_build.py`. Then `python app_phase2.py`. All speakers, many files, manifest and summary written; app shows Patent/Verification block with counts. |
| 1 | Or run `uaspeech_setup.py` and `create_uaspeech_profiles.py` (once). |
| 2 | Run `run_verification_tests.py` for CF03 (and optionally M16) with `--max_files 10` (or more). |
| 3 | Save the generated `reports/verification_report_*.md` as evidence of pipeline behavior. |
| 4 | In the app: select **Illinois_CF03** (or any Illinois_&lt;ID&gt;), run multiple files (from dropdown or full path), add corrections, then use **Generate Thesis Export** for LaTeX tables and figures. |
| 5 | Attach: (a) verification report(s), (b) thesis export folder, (c) patent build manifest and summary, (d) sample audio folder layout and README, for patent/thesis documentation. |

---

## 6. Files and folders to attach (e.g. for patent)

- **Code:** `speech-adaptation-demo/` (app, phase2, phase3, scripts).
- **Data setup:** `sample_audio/uaspeech_setup/` (vocab and basename→word lookup).
- **Sample audio:** `sample_audio/uaspeech_CF03/` and `sample_audio/uaspeech_CF03_pseudo_sentences/` (or equivalent for other speakers).
- **Patent build:** `reports/patent_build_manifest.json`, `reports/PATENT_READY_SUMMARY.txt` (from one-command build).
- **Verification:** `reports/verification_report_CF03_*.md`.
- **Thesis export:** `exports/thesis_*/` (LaTeX tables, figures, stats).
- **Docs:** `docs/VALIDATION_DATA_STRATEGY.md`, `docs/PATENT_TESTING_AND_VERIFICATION.md`, `sample_audio/uaspeech_setup/HOW_TO_RUN_UASPEECH.txt`.
