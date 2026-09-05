"""
Run UA-Speech setup and print verification steps.

Usage (from speech-adaptation-demo or project root):
  python scripts/run_uaspeech_setup_and_verify.py

UASPEECH_ROOT is read from env UASPEECH_ROOT if set, else D:\\research\\data\\UASpeech.
"""

import os
import subprocess
import sys

# Default path for Illinois UA-Speech
DEFAULT_UASPEECH_ROOT = r"D:\research\data\UASpeech"

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sample_audio = os.path.join(project_root, "sample_audio")
    uaspeech_root = os.environ.get("UASPEECH_ROOT", DEFAULT_UASPEECH_ROOT)

    if not os.path.isdir(uaspeech_root):
        print("UA-Speech root not found:", uaspeech_root)
        print("Set UASPEECH_ROOT or place data at", DEFAULT_UASPEECH_ROOT)
        sys.exit(1)

    setup_script = os.path.join(script_dir, "uaspeech_setup.py")
    if not os.path.isfile(setup_script):
        print("Not found:", setup_script)
        sys.exit(1)

    print("Running UA-Speech setup...")
    print("  UASPEECH_ROOT =", uaspeech_root)
    print("  sample_audio  =", sample_audio)
    rc = subprocess.call([
        sys.executable,
        setup_script,
        "--uaspeech_root", uaspeech_root,
        "--sample_audio_dir", sample_audio,
        "--copy_max", "50",
    ], cwd=project_root)
    if rc != 0:
        print("Setup failed with exit code", rc)
        sys.exit(rc)

    howto = os.path.join(sample_audio, "uaspeech_setup", "HOW_TO_RUN_UASPEECH.txt")
    if os.path.isfile(howto):
        print("\n" + "="*60)
        print("SETUP DONE. Next steps:")
        print("="*60)
        with open(howto, "r", encoding="utf-8") as f:
            print(f.read())
        print("="*60)
        print("To start the app:")
        print("  cd speech-adaptation-demo")
        print("  python app_phase2.py")
        print("Then open the URL in your browser and follow HOW_TO_RUN_UASPEECH.txt")
    else:
        print("Setup finished. See sample_audio/uaspeech_setup/ for generated files.")


if __name__ == "__main__":
    main()
