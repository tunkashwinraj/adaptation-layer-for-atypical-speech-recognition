"""
Create Phase 2 profiles with pre-filled vocabulary from UA-Speech setup.

Run after uaspeech_setup.py. Creates one profile per speaker (e.g. Illinois_CF03)
with custom_vocabulary loaded from uaspeech_setup/uaspeech_<ID>_vocab.txt so that
when you select the profile in the app, the vocab box is auto-filled.

Usage (from speech-adaptation-demo):
  python scripts/create_uaspeech_profiles.py
  python scripts/create_uaspeech_profiles.py --speakers CF03,M16
"""

import os
import sys

DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)
os.chdir(DEMO_DIR)

from phase2 import init_db
from phase2.profile_manager import ProfileManager


def main():
    init_db()
    setup_dir = os.path.join(DEMO_DIR, "sample_audio", "uaspeech_setup")
    if not os.path.isdir(setup_dir):
        print("Run uaspeech_setup.py first so that sample_audio/uaspeech_setup/ exists.")
        sys.exit(1)

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--speakers", default=None, help="Comma-separated e.g. CF03,M16 or leave empty for all")
    args = ap.parse_args()

    speakers = []
    for fname in os.listdir(setup_dir):
        if fname.startswith("uaspeech_") and fname.endswith("_vocab.txt"):
            # uaspeech_CF03_vocab.txt -> CF03
            mid = fname.replace("uaspeech_", "").replace("_vocab.txt", "")
            if args.speakers:
                if mid in [s.strip() for s in args.speakers.split(",")]:
                    speakers.append(mid)
            else:
                speakers.append(mid)

    if not speakers:
        print("No uaspeech_*_vocab.txt files found in", setup_dir)
        sys.exit(1)

    pm = ProfileManager()
    for speaker_id in sorted(speakers):
        vocab_path = os.path.join(setup_dir, "uaspeech_%s_vocab.txt" % speaker_id)
        with open(vocab_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ":" in ln]
        custom_vocab = []
        for ln in lines:
            part = ln.split(":", 1)
            if len(part) == 2:
                w, b = part[0].strip(), part[1].strip()
                try:
                    boost = float(b)
                except ValueError:
                    boost = 1.5
                if w:
                    custom_vocab.append({"word": w, "boost": boost})

        name = "Illinois_%s" % speaker_id
        # Check if profile with this name already exists
        existing = pm.list_profiles()
        found = next((p for p in existing if p["name"] == name), None)
        if found:
            # Update existing profile with vocab
            profile = pm.load_profile(found["user_id"])
            if profile:
                profile["custom_vocabulary"] = custom_vocab
                pm.save_profile(profile)
                print("Updated profile", name, "with", len(custom_vocab), "words")
            continue
        user_id = pm.create_profile(name, {"speaker_id": speaker_id, "source": "UASpeech"})
        profile = pm.load_profile(user_id)
        if profile:
            profile["custom_vocabulary"] = custom_vocab
            pm.save_profile(profile)
        print("Created profile", name, "with", len(custom_vocab), "words")
    print("Done. Restart the app and select an Illinois_<ID> profile; Custom Vocabulary will auto-fill.")


if __name__ == "__main__":
    main()
