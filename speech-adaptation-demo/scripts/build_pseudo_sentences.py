"""
Build pseudo-sentences from same-speaker word-level WAVs (e.g. Illinois/UA-Speech).

Reads a list of (audio_path, word) pairs, concatenates the audio with optional
silence between words, and writes one WAV per "sentence" plus a transcript file.
Use the output WAVs in sample_audio/ and the .txt as Ground Truth in the app.

Usage:
  python build_pseudo_sentences.py --list word_list.txt --output_dir ./pseudo_sentences

word_list.txt format (one per line):
  /path/to/word1.wav  word1
  /path/to/word2.wav  word2
  /path/to/word3.wav  word3
  ...
  (blank line or "---" to start next sentence)
  /path/to/next1.wav  next1
  ...

Or use --sentence_dir to point to a folder where each subfolder is a sentence
containing WAVs named by word (e.g. sentence01/hello.wav, sentence01/world.wav).
"""

import argparse
import os
import sys

try:
    import soundfile as sf
    import numpy as np
except ImportError:
    print("Need: pip install soundfile numpy")
    sys.exit(1)

SAMPLE_RATE = 16000
SILENCE_SEC = 0.25  # silence between words in pseudo-sentence


def load_wav(path: str):
    data, sr = sf.read(path)
    if sr != SAMPLE_RATE and len(data) > 0:
        try:
            from scipy import signal
            n = int(len(data) * SAMPLE_RATE / sr)
            data = signal.resample(data, n)
        except ImportError:
            # no scipy: repeat/trim to approximate target length
            n = int(len(data) * SAMPLE_RATE / sr)
            data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32), SAMPLE_RATE


def run_from_list(list_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    silence = np.zeros(int(SAMPLE_RATE * SILENCE_SEC), dtype=np.float32)
    with open(list_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f]
    sentence_num = 0
    current_audios = []
    current_words = []
    for line in lines:
        if not line or line.strip() == "---":
            if current_audios:
                sentence_num += 1
                out_name = f"pseudo_sentence_{sentence_num:03d}"
                combined = current_audios[0]
                for a in current_audios[1:]:
                    combined = np.concatenate([combined, silence, a])
                out_path = os.path.join(output_dir, f"{out_name}.wav")
                sf.write(out_path, combined, SAMPLE_RATE)
                trans_path = os.path.join(output_dir, f"{out_name}.txt")
                with open(trans_path, "w", encoding="utf-8") as tf:
                    tf.write(" ".join(current_words))
                print(f"Wrote {out_path} -> {' '.join(current_words)}")
                current_audios = []
                current_words = []
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        wav_path, word = parts[0], parts[1]
        if not os.path.isfile(wav_path):
            print(f"Skip missing: {wav_path}")
            continue
        try:
            data, _ = load_wav(wav_path)
            current_audios.append(data)
            current_words.append(word)
        except Exception as e:
            print(f"Skip {wav_path}: {e}")
    if current_audios:
        sentence_num += 1
        out_name = f"pseudo_sentence_{sentence_num:03d}"
        combined = current_audios[0]
        for a in current_audios[1:]:
            combined = np.concatenate([combined, silence, a])
        out_path = os.path.join(output_dir, f"{out_name}.wav")
        sf.write(out_path, combined, SAMPLE_RATE)
        trans_path = os.path.join(output_dir, f"{out_name}.txt")
        with open(trans_path, "w", encoding="utf-8") as tf:
            tf.write(" ".join(current_words))
        print(f"Wrote {out_path} -> {' '.join(current_words)}")
    print(f"Done. {sentence_num} pseudo-sentences in {output_dir}")


def main():
    ap = argparse.ArgumentParser(description="Build pseudo-sentences from word WAVs")
    ap.add_argument("--list", "-l", help="Path to word list file (path word per line; blank or --- separates sentences)")
    ap.add_argument("--output_dir", "-o", default="./pseudo_sentences", help="Output directory for WAVs and TXTs")
    args = ap.parse_args()
    if not args.list or not os.path.isfile(args.list):
        print("Usage: python build_pseudo_sentences.py --list word_list.txt --output_dir ./pseudo_sentences")
        print("See script docstring for word_list.txt format.")
        sys.exit(1)
    run_from_list(args.list, args.output_dir)


if __name__ == "__main__":
    main()
