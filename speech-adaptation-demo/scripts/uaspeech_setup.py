"""
End-to-end setup for UA-Speech (Illinois) data at D:\\research\\data\\UASpeech.

Run from project root or speech-adaptation-demo:
  python scripts/uaspeech_setup.py --uaspeech_root "D:\\research\\data\\UASpeech" --sample_audio_dir "speech-adaptation-demo/sample_audio" --copy_max 50

This script:
1. Parses mlf/*/*_word.mlf to get (speaker, wav_basename, word).
2. For each speaker: writes vocab file (for Custom Vocabulary) and file list (path, word).
3. Copies up to copy_max WAVs per speaker from audio/original into sample_audio/uaspeech_<speaker>/.
4. Builds pseudo-sentence list and runs build_pseudo_sentences.py to create sentence WAVs.
5. Writes HOW_TO_RUN_UASPEECH.txt with steps to run the app and verify.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys


def parse_mlf(mlf_path: str):
    """Yield (basename, word) from a *_word.mlf file. Basename is e.g. M16_B2_UW77_M5 (no .lab)."""
    with open(mlf_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # "*/M16_B2_UW77_M5.lab" -> M16_B2_UW77_M5, next line -> word
    for m in re.finditer(r'"\*/([^"]+\.lab)"\s*\n(\S+)', content):
        basename = m.group(1).replace(".lab", "")
        word = m.group(2).strip()
        if word and word != ".":
            yield basename, word


def iter_speaker_mlfs(uaspeech_root: str):
    """Yield (speaker_id, mlf_path) for each *_word.mlf under mlf/."""
    mlf_dir = os.path.join(uaspeech_root, "mlf")
    if not os.path.isdir(mlf_dir):
        return
    for name in os.listdir(mlf_dir):
        subdir = os.path.join(mlf_dir, name)
        if not os.path.isdir(subdir):
            continue
        for fname in os.listdir(subdir):
            if fname.endswith("_word.mlf"):
                yield name, os.path.join(subdir, fname)


def main():
    ap = argparse.ArgumentParser(description="Setup UA-Speech data for the Speech Adaptation app")
    ap.add_argument("--uaspeech_root", default=r"D:\research\data\UASpeech", help="Root path of UA-Speech corpus")
    ap.add_argument("--sample_audio_dir", default=None, help="Path to sample_audio (default: script_dir/../sample_audio)")
    ap.add_argument("--copy_max", type=int, default=50, help="Max WAVs to copy per speaker into sample_audio")
    ap.add_argument("--speakers", default=None, help="Comma-separated speaker IDs to use (default: all)")
    ap.add_argument("--skip_copy", action="store_true", help="Do not copy WAVs; only write vocab and file lists")
    ap.add_argument("--skip_pseudo", action="store_true", help="Do not build pseudo-sentences")
    args = ap.parse_args()

    uaspeech_root = os.path.abspath(args.uaspeech_root)
    if not os.path.isdir(uaspeech_root):
        print("UASpeech root not found:", uaspeech_root)
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sample_audio_dir = os.path.abspath(args.sample_audio_dir or os.path.join(project_root, "sample_audio"))
    os.makedirs(sample_audio_dir, exist_ok=True)

    # Try original, then normalized, then noisereduce (readme: noisereduce often best WER)
    audio_dirs = [
        os.path.join(uaspeech_root, "audio", "original"),
        os.path.join(uaspeech_root, "audio", "normalized"),
        os.path.join(uaspeech_root, "audio", "noisereduce"),
    ]
    def count_wavs(dirpath):
        n = 0
        if not os.path.isdir(dirpath):
            return 0
        for name in os.listdir(dirpath):
            path = os.path.join(dirpath, name)
            if os.path.isfile(path) and name.lower().endswith(".wav"):
                n += 1
            elif os.path.isdir(path):
                n += count_wavs(path)
        return n

    audio_base = None
    for d in audio_dirs:
        if os.path.isdir(d):
            n = count_wavs(d)
            if n > 0:
                audio_base = d
                print("Using audio dir:", d, f"({n} WAVs)")
                break
    if not audio_base:
        print("No audio folder with WAVs found. Tried:", audio_dirs)
        sys.exit(1)

    speaker_filter = set(s.strip() for s in (args.speakers or "").split(",")) if args.speakers else None

    # 1) Parse all MLFs, collect per-speaker (wav_path, word)
    per_speaker = {}
    for speaker_id, mlf_path in iter_speaker_mlfs(uaspeech_root):
        if speaker_filter and speaker_id not in speaker_filter:
            continue
        if speaker_id not in per_speaker:
            per_speaker[speaker_id] = []
        for basename, word in parse_mlf(mlf_path):
            # Try flat: audio_base/basename.wav, then speaker subfolder: audio_base/CF03/basename.wav
            wav_path = os.path.join(audio_base, basename + ".wav")
            if not os.path.isfile(wav_path):
                wav_path = os.path.join(audio_base, speaker_id, basename + ".wav")
            if os.path.isfile(wav_path):
                per_speaker[speaker_id].append((wav_path, word))

    if not per_speaker:
        print("No speaker data found. Check mlf/ and audio/original.")
        sys.exit(1)

    print("Speakers found:", list(per_speaker.keys()))
    for sid, pairs in per_speaker.items():
        print(f"  {sid}: {len(pairs)} (path, word) pairs")

    # 2) Write vocab and file list per speaker; optionally copy WAVs
    out_dir = os.path.join(sample_audio_dir, "uaspeech_setup")
    os.makedirs(out_dir, exist_ok=True)

    for speaker_id, pairs in per_speaker.items():
        # Unique words for Custom Vocabulary (word:1.5 per line)
        words = list(dict.fromkeys(w for _, w in pairs))
        vocab_path = os.path.join(out_dir, f"uaspeech_{speaker_id}_vocab.txt")
        with open(vocab_path, "w", encoding="utf-8") as f:
            for w in words:
                f.write(f"{w}:1.5\n")
        print("Wrote", vocab_path, f"({len(words)} words)")

        # File list: path \t word (for reference and for pseudo-sentences)
        list_path = os.path.join(out_dir, f"uaspeech_{speaker_id}_files.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for path, word in pairs:
                f.write(f"{path}\t{word}\n")
        print("Wrote", list_path, f"({len(pairs)} entries)")

        # Basename -> word (for quick Ground Truth lookup when you pick a file from dropdown)
        basename_path = os.path.join(out_dir, f"uaspeech_{speaker_id}_basename_to_word.txt")
        with open(basename_path, "w", encoding="utf-8") as f:
            for path, word in pairs:
                f.write(f"{os.path.basename(path)}\t{word}\n")
        print("Wrote", basename_path, "(for Ground Truth lookup)")

        # Copy up to copy_max WAVs to sample_audio/uaspeech_<speaker>/
        if not args.skip_copy and args.copy_max > 0:
            dest_dir = os.path.join(sample_audio_dir, f"uaspeech_{speaker_id}")
            os.makedirs(dest_dir, exist_ok=True)
            copied = 0
            for path, word in pairs:
                if copied >= args.copy_max:
                    break
                if not os.path.isfile(path):
                    continue
                fname = os.path.basename(path)
                dest = os.path.join(dest_dir, fname)
                if not os.path.isfile(dest) or os.path.getmtime(path) > os.path.getmtime(dest):
                    shutil.copy2(path, dest)
                    copied += 1
            print(f"Copied {copied} WAVs to {dest_dir}")

    # 3) Build pseudo-sentences (e.g. 5 words per sentence) per speaker
    if not args.skip_pseudo:
        words_per_sentence = 5
        for speaker_id, pairs in per_speaker.items():
            list_path = os.path.join(out_dir, f"uaspeech_{speaker_id}_files.txt")
            pseudo_list = os.path.join(out_dir, f"uaspeech_{speaker_id}_pseudo_list.txt")
            with open(pseudo_list, "w", encoding="utf-8") as f:
                for i in range(0, min(100, len(pairs)), words_per_sentence):
                    chunk = pairs[i : i + words_per_sentence]
                    for path, word in chunk:
                        f.write(f"{path}\t{word}\n")
                    f.write("---\n")
            pseudo_out = os.path.join(sample_audio_dir, f"uaspeech_{speaker_id}_pseudo_sentences")
            os.makedirs(pseudo_out, exist_ok=True)
            build_script = os.path.join(script_dir, "build_pseudo_sentences.py")
            if os.path.isfile(build_script):
                rc = subprocess.call(
                    [sys.executable, build_script, "--list", pseudo_list, "--output_dir", pseudo_out],
                    cwd=project_root,
                )
                if rc == 0:
                    print("Built pseudo-sentences in", pseudo_out)
                else:
                    print("build_pseudo_sentences.py failed with", rc)
            else:
                print("Skipped pseudo-sentences (build_pseudo_sentences.py not found)")

    # 4) Write HOW_TO_RUN
    howto = os.path.join(out_dir, "HOW_TO_RUN_UASPEECH.txt")
    with open(howto, "w", encoding="utf-8") as f:
        f.write("UA-Speech setup complete.\n\n")
        f.write("1) RUN THE APP (Phase 2 recommended)\n")
        f.write("   cd speech-adaptation-demo\n")
        f.write("   python app_phase2.py\n\n")
        f.write("2) IN THE APP\n")
        f.write("   - Create a profile (e.g. Illinois_M16) or use existing.\n")
        f.write("   - Demo tab: In 'Built-in Demo Audio', choose a file from uaspeech_<SpeakerID> folder.\n")
        f.write("   - Open uaspeech_setup/uaspeech_<SpeakerID>_vocab.txt and paste its contents into 'Custom Vocabulary'.\n")
        f.write("   - Paste the single word (or phrase) for that file into 'Ground Truth' (see _files.txt for path->word).\n")
        f.write("   - Click 'Run Pipeline'. Then use Continual Learning to submit corrections for wrong words.\n\n")
        f.write("3) FILES CREATED\n")
        f.write("   - uaspeech_<ID>_vocab.txt           -> paste into Custom Vocabulary.\n")
        f.write("   - uaspeech_<ID>_files.txt          -> full path and word for each WAV.\n")
        f.write("   - uaspeech_<ID>_basename_to_word.txt -> filename -> word (for Ground Truth lookup).\n")
        f.write("   - sample_audio/uaspeech_<ID>/      -> WAVs listed in Built-in Demo Audio.\n")
        if not args.skip_pseudo:
            f.write("   - sample_audio/uaspeech_<ID>_pseudo_sentences/ -> pseudo-sentence WAVs and .txt transcripts.\n")
        f.write("\n4) VERIFICATION\n")
        f.write("   - Run 5-10 different WAVs from one speaker; add corrections where ASR is wrong.\n")
        f.write("   - Check Analytics tab and 'Generate Thesis Export' for WER tables and figures.\n")
    print("Wrote", howto)
    print("Done. See", howto, "for run instructions.")


if __name__ == "__main__":
    main()
