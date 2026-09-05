# Explain Everything Like a Child

This document explains **what this project is**, **what happens when you run things**, and **what every part of the screen does** — in very simple words.

---

## 1. The Big Picture: What Problem Are We Solving?

Imagine someone whose speech is hard to understand (e.g. because of a disability or an accent). When they talk into a normal phone or computer:

- **Normal speech recognition** often gets the words **wrong**.
- We want to **help the computer understand them better** by:
  1. Using a **generic** speech-to-text (Baseline).
  2. Then **personalizing** it for that person (their words, their way of saying things).
  3. Then **cleaning up** the text with an AI so it reads clearly (Semantic Repair).

So: **we are building a system that listens to speech and turns it into correct, clear text — and we want to prove it works with real data** (for a patent or thesis).

---

## 2. What Is “Data” Here?

- **Audio files** = recordings of people saying words or sentences (e.g. WAV files).
- **Speaker** = one person (e.g. “CF03” is one speaker in the Illinois dataset).
- **Profile** = one “user” in our app: we save their name and a list of words they use (vocabulary).
- **Ground truth** = what the person **actually said** (so we can check if the computer got it right).
- **Vocabulary** = list of words we tell the speech engine to prefer for that person (e.g. “Atorvastatin”, “Calgary”).

We use the **Illinois UA-Speech** dataset: real recordings of people saying single words. We copy those files into our project, build a list of words per speaker, and create one **profile** per speaker (e.g. **Illinois_CF03**). That way the app has **multiple speakers**, **many audio files**, and **pre-filled vocabulary** — all the “data” we need to show the system works.

---

## 3. What Happens When You Run the One Command?

When you run:

```text
python scripts/patent_ready_full_build.py
```

the computer does these steps **in order**:

| Step | What happens in simple words |
|------|------------------------------|
| **1** | It looks at the Illinois data folder (e.g. `D:\research\data\UASpeech`). It finds **all speakers** (e.g. CF03, M16, …). For each speaker it reads the “answer key” (which file = which word) and copies **many** WAV files (e.g. 150 per speaker) into our project under `sample_audio/uaspeech_CF03/`, etc. |
| **2** | It builds **pseudo-sentences**: it groups several words (e.g. 5) into a list and creates “sentence” audio by concatenating those word files. So we get both **single-word** and **sentence-level** data. |
| **3** | It creates **one profile per speaker** in the app (e.g. Illinois_CF03, Illinois_M16). Each profile gets a **vocabulary file** — the list of words that speaker said. So when you pick that profile in the app, the “Custom Vocabulary” box is **already filled** with that speaker’s words. |
| **4** | (Optional) If you set **seed_sessions**, it runs the **pipeline** (see below) on a few files per speaker and **saves the results** in the database. Then the **Analytics** and **Thesis Export** tabs already have data, without you clicking “Run Pipeline” yourself. |
| **5** | It writes a **manifest** file (`reports/patent_build_manifest.json`) that says: how many speakers, how many profiles, how many audio files. The **frontend** reads this and shows it in the “Patent / Verification Summary” box. |

So: **one command** = copy data, build sentences, create profiles, optionally run the pipeline a few times, and write a summary. After that, you **only** need to open the app — no other commands.

---

## 4. What Is the “Pipeline”?

The **pipeline** is the core of what happens when you click **“Run Pipeline”** in the app. For **one** audio file, the computer does:

| Stage | Name | What it does |
|-------|------|----------------|
| **1** | **Baseline ASR** | Sends the audio to a generic speech-to-text (e.g. Deepgram) **without** any personalization. You get a first transcript. |
| **2** | **Personalized ASR** | Sends the **same** audio to the same engine, but **with** this user’s vocabulary (and any learned pronunciation patterns). You get a second transcript — hopefully closer to what they said. |
| **3** | **Semantic Repair** | Takes the personalized transcript and sends it to an AI (e.g. OpenAI) to fix grammar, clarity, and wording. You get a final, clean sentence. |

So: **one audio in → three texts out** (baseline, personalized, repaired). All the tables and numbers in the app (WER, similarity, etc.) are **comparing these three** and comparing them to **ground truth** if you type it in.

---

## 5. What Is the “Frontend”? What Are All the Fields?

The **frontend** is the **web page** you see when you run `python app_phase2.py`. It’s built with Gradio. Below is **every main part** and what it means.

### At the very top

- **“Patent / Verification Summary”** (accordion)
  - Short text explaining the **three layers** (Baseline → Personalized → Semantic Repair).
  - If you ran the patent build, it also shows: **how many speakers**, **how many profiles**, **how many audio files** are loaded. So you can see “we have a lot of data” without running anything else.

### Top row

- **Select Profile** (dropdown)
  - Choose **which user** you are testing as. Each profile has a name (e.g. Illinois_CF03) and an internal ID. When you select a profile, the **Custom Vocabulary** box below is **auto-filled** with that speaker’s word list (so you don’t type it by hand).
- **Create New Profile** (button)
  - Creates a new empty profile (name + optional speech characteristics). You’d use this for a new person, not for the pre-built Illinois speakers.

### Settings (accordion, usually closed)

- **Enable Continual Learning** – If on, when you submit **corrections** (in the Continual Learning tab), the system saves them and can use them to improve.
- **Enable Multi-Model Comparison** – If on, you can compare different speech engines in the Model Comparison tab.
- **Enable Adaptive Interaction** – If on, the system can adjust (e.g. suggest retries) based on how often things go wrong.

### Tab: **Demo**

This is the main tab where you **run the pipeline** on one audio.

**Inputs (how you give audio and context):**

| Field | What it is |
|-------|------------|
| **Record Audio (Mic)** | Record with your microphone. |
| **Domain Hints (optional)** | Short text to help the Semantic Repair step (e.g. “medical”, “shopping”). |
| **Upload Audio File** | Choose a file from your computer (WAV, MP3, etc.). |
| **Built-in Demo Audio** | A **dropdown list** of audio files that are **already in the project** — e.g. under `sample_audio/uaspeech_CF03/` or `sample_audio/uaspeech_CF03_pseudo_sentences/`. You pick one file from the list. |
| **Or paste direct audio URL** | A link to an audio file on the internet; the app downloads it and runs the pipeline. |
| **Or full path to local WAV** | Type the full path to a WAV on your PC (e.g. `D:\research\data\UASpeech\audio\original\CF03\file.wav`). Use this when the file is not in the dropdown. |
| **Custom Vocabulary (word:boost)** | List of words (and optional boost) for the **personalized** ASR. When you select an Illinois profile, this is **filled automatically** from that speaker’s vocabulary. |
| **Ground Truth (optional)** | What the person **actually said** in that audio. If you fill this, the app can compute **WER/CER** (how wrong the computer was) for each stage. For Illinois single-word files, you can look up the word in `sample_audio/uaspeech_setup/uaspeech_CF03_basename_to_word.txt`. |
| **Task Context for LATTEScore (optional)** | Optional description of the task (e.g. “ordering medication”) for an extra metric. |
| **Run Pipeline** (button) | Click this to run: Baseline ASR → Personalized ASR → Semantic Repair on the chosen audio. |

**Outputs (what you see after Run Pipeline):**

| Field | What it is |
|-------|------------|
| **Baseline ASR Transcript** | The text from the **generic** speech-to-text (no personalization). |
| **Personalized ASR Transcript** | The text from the **same** engine **with** this user’s vocabulary. |
| **Semantic Repair Output** | The **final** text after the AI cleaned it up. |
| **Baseline / Personalized Word Timings** | When each word was said (start/end times). |
| **Side-by-Side Comparison** | A table: Baseline vs Personalized vs Repaired transcripts and confidence. |
| **Similarity Metrics** | How similar the three texts are (Jaccard, Cosine, Token Overlap). |
| **WER/CER vs Ground Truth** | If you entered ground truth: how many word/character errors at each stage (lower = better). |
| **Confidence Metrics** | How confident the ASR was (per stage). |
| **Timing / Readability / Grammar / Error Analysis / Repair Impact** | Extra tables that describe the transcripts (timing, readability, grammar issues, what changed between stages). |
| **Top Replacement Pairs** | Which words were “replaced” (e.g. Baseline said X, Personalized said Y). |
| **Advanced Metrics** | SemScore, MER, Task Success, etc. |
| **Adaptive Interaction State** | Internal state if you use adaptive interaction (e.g. retries, frustration score). |
| **Frustration indicator** | A short message like “😊 Mode: INTEGRATION (frustration score 0.00)”. |
| **Confirmation / Fallback markdown** | Short messages from the system (e.g. confirmation of an action). |

So on the **Demo** tab: you **choose a profile**, **choose an audio** (mic, upload, dropdown, URL, or path), optionally **ground truth**, then click **Run Pipeline**. The rest of the tab is **results** of the three stages and all the comparisons.

### Tab: **Continual Learning**

- **Correct This Transcript** – You type the **correct** text (when the ASR was wrong).
- **Correction Context (optional)** – Optional note (e.g. “medical term”).
- **Submit Correction** – Saves this correction for the current profile. Over time the system learns (e.g. pronunciation patterns).
- **Correction History** – Table of past corrections.
- **Pronunciation Patterns** – Table of patterns the system learned (e.g. “it often heard X when they said Y”).

### Tab: **Pronunciation Patterns**

- **Refresh Patterns** – Reload the table of learned patterns for the selected profile.
- **Detected Patterns** – Same as above: what the system learned from corrections.

### Tab: **Model Comparison**

- You run **multiple** ASR models on the same audio and compare. **Model Outputs** = table of each model’s transcript; **Recommended Model** and **Ensemble Output** = suggested best and combined result.

### Tab: **Analytics**

- **Charts** – WER over time, SemScore over time, Task Success (if you have enough runs).
- **Refresh Analytics** – Reload charts from the database.
- **Generate Thesis Export** – Creates a folder with **LaTeX tables and figures** (for thesis or patent document).
- **Thesis Export Directory** – Shows where that folder was written.

### Tab: **Profile Management**

- Create / export / import **profiles** (name, speech characteristics). The patent build already created Illinois_* profiles; you can add more here.

### Tab: **Export**

- Export data in different formats (LaTeX, CSV, JSON) for reports.

---

## 6. What Are We Actually Doing and What Do We Expect?

**What we are doing:**

1. **One-time setup:** Run `patent_ready_full_build.py` so we have **many speakers**, **many audio files**, **profiles with vocabulary**, and (optionally) some **pre-run pipeline results** in the database.
2. **Open the app:** Run `app_phase2.py` and open the URL in the browser.
3. **See the summary:** The “Patent / Verification Summary” shows that we have X speakers, Y profiles, Z audio files — **no extra commands**.
4. **Run the pipeline:** Pick a profile (e.g. Illinois_CF03), pick an audio from **Built-in Demo Audio** or type a path, optionally paste **ground truth** from the basename_to_word file, click **Run Pipeline**.
5. **Look at the results:** We see three transcripts (Baseline, Personalized, Repaired) and all the tables (WER, similarity, etc.). If we gave ground truth, we **expect** Personalized and Repaired to often have **lower WER** than Baseline — that’s the “proof” that personalization and repair help.
6. **Optional:** Use **Continual Learning** to correct mistakes, then **Analytics** and **Thesis Export** to get charts and LaTeX for the patent/thesis.

**What we expect:**

- **Baseline ASR** often gets words wrong for difficult speech.
- **Personalized ASR** (with that speaker’s vocabulary) should get **more words right** (lower WER when we have ground truth).
- **Semantic Repair** should produce **cleaner, more readable** text.
- The **manifest** and the **Patent / Verification Summary** show that we have **enough data** (multiple speakers, many files, word- and sentence-level) to support our claims — **patent-ready verification** without running any other programs.

---

## 7. Short Glossary

| Word | Simple meaning |
|------|----------------|
| **ASR** | Automatic Speech Recognition = turning speech into text. |
| **Baseline** | The “default” engine without any personalization. |
| **Personalized** | Same engine, but with this user’s vocabulary and patterns. |
| **Semantic Repair** | AI step that fixes grammar and clarity of the transcript. |
| **WER** | Word Error Rate = how many words are wrong compared to ground truth (lower is better). |
| **CER** | Character Error Rate = same idea but for characters. |
| **Ground truth** | The correct answer (what the person really said). |
| **Profile** | One “user” in the app (name + vocabulary + optional characteristics). |
| **Pipeline** | The full sequence: Baseline ASR → Personalized ASR → Semantic Repair. |
| **Manifest** | A small file that lists how many speakers, profiles, and audio files we have. |
| **Patent-ready** | We have enough data and a clear process so we can show and document the system for a patent. |

If you want, we can go through **one** tab (e.g. only Demo) line by line with a concrete example (e.g. “I pick Illinois_CF03, I pick file X, I paste word Y as ground truth, I click Run, and I see …”).
