# Validation Data Strategy: Strong Proof for Patent & Thesis

Your Illinois (UA-Speech) data is **mostly 1–3 words per file**. You need:

1. **Sentence-length audio** – to show the full pipeline on realistic utterances.
2. **Repeated same-user data** – to prove the personalized layer learns from one speaker’s vocabulary over time.
3. **Clear evidence** – for patent and thesis validation.

Below: how to get that proof with what you have **plus** a few extra sources.

---

## Part 1: Use Your Illinois Data for “Same User, Repeated Vocabulary” Proof

UA-Speech is **ideal for proving personalization**, even though each file is short:

- **Same speaker** says the **same vocabulary** (hundreds of words) across many files.
- You can treat **each word file as one “utterance”** and show that as you add that speaker’s words to the personalized layer and correct errors, **WER drops** and **pronunciation patterns** emerge.

### How to run this validation (with your current app)

1. **One profile per Illinois speaker**
   - In **app_phase2.py** create a profile, e.g. `Illinois_Speaker_01`.

2. **Build that speaker’s vocabulary once**
   - From the Illinois corpus you have a **word list** (and possibly multiple repetitions per word). Put that speaker’s **full word list** into **Custom Vocabulary** (e.g. `word:1.5` per line). That is your “personalized layer” for that user.

3. **Run in batches**
   - Select **Built-in Demo Audio** (after copying that speaker’s WAVs into `sample_audio/`), or upload files one by one.
   - For each file: run pipeline, then in **Continual Learning** submit **corrections** when ASR is wrong (use the known word as correction).
   - Over 50–100+ files from the **same speaker**, you get:
     - Many **corrections** for the same words (repeated failures → repeated corrections).
     - **Continual learning** updating vocabulary.
     - **Pronunciation Patterns** tab showing that speaker’s systematic misrecognitions (e.g. “medication” → “medication” after learning).

4. **What to report for patent/thesis**
   - **Table:** WER (Baseline vs Personalized vs Repaired) **per speaker**, or **before vs after** adding their vocabulary + corrections.
   - **Table:** Number of corrections per speaker, vocabulary size over time, and (if you log it) WER by “session” (e.g. first 20 vs last 20 files).
   - **Figure:** WER over “session” or over correction count (from Analytics tab / thesis export).
   - **Claim:** “The system improves recognition for the same user as it is exposed to repeated vocabulary and corrections from that user.”

So: **you already have the right data for “repeated same user”** – use one profile per Illinois speaker, their full word list in Custom Vocabulary, and many of their 1–3 word files with corrections. That gives strong proof for the **personalized layer** even without long sentences.

---

## Part 2: Getting Sentence-Length Data (Long Utterances)

For **full sentences**, you have three options.

### Option A: TORGO (dysarthric sentences) – best fit

- **What it is:** Dysarthric speakers (CP/ALS) + controls; **sentences** (e.g. 162 + 460 read sentences) and some spontaneous speech.
- **Where:** LDC: **TORGO Database of Dysarthric Articulation** – https://catalog.ldc.upenn.edu/LDC2012S02  
- **Access:** LDC membership (institution or paid). After you get it, copy sentence WAVs + transcripts into `sample_audio/` (or a subfolder) and use **Ground Truth** in the app.
- **Why it matters:** Proves your pipeline on **sentence-level atypical speech**, not just isolated words. Use same flow: profile per speaker, custom vocab from their vocabulary, run sentences, report WER by stage.

### Option B: Scripted sentences with your Illinois vocabulary

- **Idea:** Reuse the **same words** you already have from Illinois, but in **sentence form**.
  - Examples: “I need my **Atorvastatin**”, “Turn on the **lights**”, “**Calgary** weather tomorrow.”
- **How:**
  - Option B1: **Record yourself** (or a colleague) reading 20–30 short sentences that use those words. You get WAV + known transcript. Put in `sample_audio/` and run in the app with that vocabulary.
  - Option B2: **Small in-house study** – 2–3 participants (atypical speech if possible) each read 10–20 scripted sentences (your Phase 3 task prompts or similar). One profile per participant; run through app_phase2; export WER and corrections.
- **Why it matters:** You control the vocabulary and the sentences; proof is **reproducible** and ties directly to your “personalized layer” (same words, now in sentences).

### Option C: Combine word-level Illinois data into “pseudo-sentences”

- **Idea:** Take **several consecutive word files from the same speaker** and treat them as one “sentence” (e.g. concatenate audio, and concatenate transcripts for Ground Truth).
- **How:** Write a small script (Python + pydub/soundfile) that:
  - Reads a list of that speaker’s WAV paths in order.
  - Concatenates them (optional: 0.3 s silence between words).
  - Saves one WAV per “sentence” and a text file with the combined transcript.
- **Use in app:** Load the concatenated WAVs into `sample_audio/`, use the combined transcript as Ground Truth. Custom Vocabulary = that speaker’s word list.
- **Caveat:** Not natural prosody, but still shows the pipeline on **multi-word utterances** and same-speaker repeated vocabulary. Acceptable for a proof-of-concept or an extra experiment.

---

## Part 3: Suggested Validation Plan for Patent / Thesis

| Experiment | Data | What you show |
|------------|------|----------------|
| **1. Same-speaker repeated words** | Illinois (UA-Speech) – one speaker, many word files | WER by stage (Baseline / Personalized / Repaired); effect of adding that speaker’s vocabulary + corrections; pronunciation patterns. Proves **personalization from repeated exposure to one user’s vocabulary**. |
| **2. Multiple speakers, same protocol** | Illinois – 2–3 more speakers | Same metrics per speaker; show the approach generalizes across speakers. |
| **3. Sentence-level (if you get TORGO)** | TORGO sentence WAVs + transcripts | WER and repair on **full sentences**; same pipeline, different data type. |
| **4. Scripted sentences (in-house)** | Your own 20–30 sentences using Illinois-style vocabulary, or Phase 3 task prompts | End-to-end proof on **controlled sentences**; good for “real-world tasks” narrative. |
| **5. Longitudinal (optional)** | Same Illinois speaker, split into “Session 1” vs “Session 2” (e.g. first 50 vs last 50 files) | WER and vocabulary growth over “sessions” in app_phase2; supports “improves with use” claim. |

For **patent**, the strongest pieces are:

- **Repeated same-user vocabulary** (Illinois, one profile per speaker, many files + corrections).
- **Sentence-level improvement** (TORGO or scripted/in-house sentences).
- **Explicit metrics:** WER/CER by stage, effect of custom vocabulary, and (if you log it) improvement over “sessions” or correction count.

---

## Part 4: Where to Put Data and How to Run

- **Word-level (Illinois):** Keep WAVs in `sample_audio/` (or a subfolder like `sample_audio/illinois_speaker01/`). In the app, use **Built-in Demo Audio** or **Upload**. One **profile per speaker** in app_phase2; paste that speaker’s **word list** in Custom Vocabulary; run files and submit corrections in Continual Learning.
- **Sentence-level (TORGO or your own):** Same: put WAVs in `sample_audio/`, use **Ground Truth** with the sentence transcript, run pipeline and (for Phase 2) corrections and analytics.
- **Export for papers/patent:** Use **Analytics** tab and **Generate Thesis Export** in app_phase2 to get tables and figures; export study CSV from app_study_simple if you run in-house sentence studies.

---

## Summary

- **Illinois (1–3 word files)** is enough for **strong same-user, repeated-vocabulary** validation: one profile per speaker, their word list, many files, corrections → WER and pronunciation learning. Use it as your main proof for the **personalized layer**.
- **Sentences** come from: **TORGO** (best, LDC), **scripted sentences** with your vocabulary (you record or run a small study), or **concatenated word files** from Illinois as pseudo-sentences.
- Combining **Experiment 1–2** (Illinois, same user + multiple speakers) with **Experiment 3 or 4** (sentences) gives you the **strong proof** you need for patent and thesis.
