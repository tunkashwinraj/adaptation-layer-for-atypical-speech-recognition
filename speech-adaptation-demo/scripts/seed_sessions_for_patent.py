r"""
Seed the database with pipeline runs for patent/verification (so Analytics has data).
Called by patent_ready_full_build.py. Requires API keys.
"""

import os
import sys

DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)
os.chdir(DEMO_DIR)

from dotenv import load_dotenv
load_dotenv()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--speakers", required=True, help="Comma-separated e.g. CF03,M16")
    ap.add_argument("--files_per_speaker", type=int, default=5)
    args = ap.parse_args()
    speakers = [s.strip() for s in args.speakers.split(",") if s.strip()]

    if not os.getenv("DEEPGRAM_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        print("DEEPGRAM_API_KEY and OPENAI_API_KEY required for seeding.")
        sys.exit(1)

    from app_phase2 import run_pipeline_phase2
    from phase2.profile_manager import ProfileManager

    pm = ProfileManager()
    profiles = pm.list_profiles()
    sample_audio = os.path.join(DEMO_DIR, "sample_audio")
    setup_dir = os.path.join(sample_audio, "uaspeech_setup")

    for speaker_id in speakers:
        profile_label = next((f"{p['user_id']} | {p['name']}" for p in profiles if p["name"] == "Illinois_%s" % speaker_id), None)
        if not profile_label:
            print("Profile not found for", speaker_id)
            continue
        vocab_path = os.path.join(setup_dir, "uaspeech_%s_vocab.txt" % speaker_id)
        basename_path = os.path.join(setup_dir, "uaspeech_%s_basename_to_word.txt" % speaker_id)
        if not os.path.isfile(vocab_path) or not os.path.isfile(basename_path):
            continue
        with open(vocab_path, "r", encoding="utf-8") as f:
            vocab_text = f.read()
        gt_map = {}
        with open(basename_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t", 1)
                if len(parts) == 2:
                    gt_map[parts[0]] = parts[1]
        wav_dir = os.path.join(sample_audio, "uaspeech_%s" % speaker_id)
        if not os.path.isdir(wav_dir):
            continue
        wavs = sorted([f for f in os.listdir(wav_dir) if f.lower().endswith(".wav")])[: args.files_per_speaker]
        for fname in wavs:
            path = os.path.join(wav_dir, fname)
            word = gt_map.get(fname, "")
            try:
                run_pipeline_phase2(
                    profile_label,
                    None,
                    None,
                    path,
                    "",
                    "",
                    vocab_text,
                    "",
                    word,
                    "",
                    True,
                    True,
                )
                print("  Seeded:", speaker_id, fname)
            except Exception as e:
                print("  Skip %s: %s" % (fname, e))
    print("Seeding done.")


if __name__ == "__main__":
    main()
