r"""
Single entry point: build a complete, patent-ready verification dataset and app state.

Run once (no other commands needed):
  cd speech-adaptation-demo
  python scripts/patent_ready_full_build.py

Optional:
  python scripts/patent_ready_full_build.py --uaspeech_root "D:\research\data\UASpeech" --copy_max 200 --seed_sessions 5

This script:
1. Runs UA-Speech setup for ALL speakers: copies many WAVs per speaker, builds pseudo-sentences.
2. Creates one profile per speaker with full vocabulary (Illinois_CF03, Illinois_M16, ...).
3. Optionally seeds the DB by running the pipeline on a few files per speaker (requires API keys).
4. Writes a manifest (reports/patent_build_manifest.json) and summary for the frontend.
After running, launch the app and you will see multiple speakers, many audio files, and full data.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)
os.chdir(DEMO_DIR)


def run_setup(uaspeech_root: str, copy_max: int, speakers: str = None, skip_pseudo: bool = False) -> list:
    """Run uaspeech_setup; return list of speaker IDs that had data."""
    script = os.path.join(os.path.dirname(__file__), "uaspeech_setup.py")
    cmd = [
        sys.executable,
        script,
        "--uaspeech_root", uaspeech_root,
        "--sample_audio_dir", os.path.join(DEMO_DIR, "sample_audio"),
        "--copy_max", str(copy_max),
    ]
    if speakers:
        cmd.extend(["--speakers", speakers])
    if skip_pseudo:
        cmd.append("--skip_pseudo")
    r = subprocess.run(cmd, cwd=DEMO_DIR)
    if r.returncode != 0:
        return []
    # Infer speakers from created vocab files
    setup_dir = os.path.join(DEMO_DIR, "sample_audio", "uaspeech_setup")
    out = []
    if os.path.isdir(setup_dir):
        for f in os.listdir(setup_dir):
            if f.startswith("uaspeech_") and f.endswith("_vocab.txt"):
                mid = f.replace("uaspeech_", "").replace("_vocab.txt", "")
                out.append(mid)
    return sorted(out)


def run_create_profiles(speakers: list = None):
    """Create Illinois_<ID> profiles with vocab."""
    script = os.path.join(os.path.dirname(__file__), "create_uaspeech_profiles.py")
    cmd = [sys.executable, script]
    if speakers:
        cmd.extend(["--speakers", ",".join(speakers)])
    subprocess.run(cmd, cwd=DEMO_DIR, check=True)


def count_audio_files(sample_audio_dir: str) -> int:
    n = 0
    ext = {".wav", ".mp3", ".flac", ".m4a"}
    for root, _, files in os.walk(sample_audio_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() in ext:
                n += 1
    return n


def seed_sessions(speakers: list, files_per_speaker: int):
    """Run pipeline on a few files per speaker via subprocess (requires API keys)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    if not os.getenv("DEEPGRAM_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        print("Skipping session seeding (DEEPGRAM_API_KEY / OPENAI_API_KEY not set).")
        return
    script = os.path.join(os.path.dirname(__file__), "seed_sessions_for_patent.py")
    r = subprocess.run(
        [sys.executable, script, "--speakers", ",".join(speakers), "--files_per_speaker", str(files_per_speaker)],
        cwd=DEMO_DIR,
    )
    if r.returncode != 0:
        print("Session seeding exited with code", r.returncode)


def write_manifest(speakers: list, total_audio: int, report_path: str):
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    manifest = {
        "built_at": datetime.utcnow().isoformat() + "Z",
        "speakers": speakers,
        "profile_count": len(speakers),
        "profile_names": ["Illinois_%s" % s for s in speakers],
        "total_audio_files": total_audio,
        "patent_ready": True,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    summary_path = os.path.join(DEMO_DIR, "reports", "PATENT_READY_SUMMARY.txt")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Patent-ready full build completed.\n")
        f.write("Speakers: %s\n" % ", ".join(speakers))
        f.write("Profiles: %d (Illinois_<ID>)\n" % len(speakers))
        f.write("Total audio files in app: %d\n" % total_audio)
        f.write("Manifest: %s\n" % report_path)
        f.write("\nLaunch the app: python app_phase2.py\n")
        f.write("Select any Illinois_<ID> profile; Custom Vocabulary auto-fills. Choose audio and run pipeline.\n")


def main():
    ap = argparse.ArgumentParser(description="One-command patent-ready full build")
    ap.add_argument("--uaspeech_root", default=r"D:\research\data\UASpeech")
    ap.add_argument("--copy_max", type=int, default=150, help="WAVs to copy per speaker")
    ap.add_argument("--speakers", default=None, help="Comma-separated or leave empty for all")
    ap.add_argument("--seed_sessions", type=int, default=5, help="Pipeline runs per speaker to seed DB (0 to skip)")
    ap.add_argument("--skip_pseudo", action="store_true", help="Skip building pseudo-sentences")
    args = ap.parse_args()

    uaspeech_root = os.path.abspath(args.uaspeech_root)
    if not os.path.isdir(uaspeech_root):
        print("UASpeech root not found:", uaspeech_root)
        sys.exit(1)

    print("=" * 60)
    print("PATENT-READY FULL BUILD")
    print("=" * 60)
    print("Step 1: UA-Speech setup (all speakers, copy_max=%d) ..." % args.copy_max)
    speakers = run_setup(uaspeech_root, args.copy_max, args.speakers, args.skip_pseudo)
    if not speakers:
        print("No speakers with data. Check UASpeech path and mlf/ + audio/original/<ID>/.")
        sys.exit(1)
    print("Speakers with data:", speakers)

    print("\nStep 2: Create profiles with vocabulary ...")
    run_create_profiles(speakers)

    sample_audio_dir = os.path.join(DEMO_DIR, "sample_audio")
    total_audio = count_audio_files(sample_audio_dir)
    print("\nTotal audio files in sample_audio:", total_audio)

    if args.seed_sessions > 0:
        print("\nStep 3: Seed sessions (run pipeline on %d files per speaker) ..." % args.seed_sessions)
        seed_sessions(speakers, args.seed_sessions)
    else:
        print("\nStep 3: Skipped (--seed_sessions 0).")

    reports_dir = os.path.join(DEMO_DIR, "reports")
    manifest_path = os.path.join(reports_dir, "patent_build_manifest.json")
    write_manifest(speakers, total_audio, manifest_path)
    print("\nManifest written:", manifest_path)
    print("=" * 60)
    print("Done. Run: python app_phase2.py")
    print("You will see %d profiles and %d audio files. No other commands needed." % (len(speakers), total_audio))
    print("=" * 60)


if __name__ == "__main__":
    main()
