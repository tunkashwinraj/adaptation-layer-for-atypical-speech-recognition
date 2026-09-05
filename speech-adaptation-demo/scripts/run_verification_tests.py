r"""
Run pipeline verification tests on UA-Speech data and generate a testing report.

Usage (from speech-adaptation-demo):
  python scripts/run_verification_tests.py --uaspeech_root "D:\research\data\UASpeech" --speaker CF03 --max_files 10

Requires: .env with DEEPGRAM_API_KEY and OPENAI_API_KEY.
"""

import argparse
import os
import sys
from datetime import datetime

# Run from speech-adaptation-demo so imports work
DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)
os.chdir(DEMO_DIR)

from dotenv import load_dotenv
load_dotenv()

from analytics import wer
from asr_processor import baseline_asr, personalized_asr
from semantic_repair import semantic_repair
from utils import parse_custom_vocab, load_audio_bytes


def find_speaker_wavs(uaspeech_root: str, speaker_id: str, audio_subdir: str = "original", max_files: int = 10):
    """Return list of (wav_path, ground_truth_word) for the speaker. Uses MLF for ground truth."""
    mlf_dir = os.path.join(uaspeech_root, "mlf", speaker_id)
    mlf_path = None
    if os.path.isdir(mlf_dir):
        for f in os.listdir(mlf_dir):
            if f.endswith("_word.mlf"):
                mlf_path = os.path.join(mlf_dir, f)
                break
    if not mlf_path or not os.path.isfile(mlf_path):
        return []

    import re
    basename_to_word = {}
    with open(mlf_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    for m in re.finditer(r'"\*/([^"]+\.lab)"\s*\n(\S+)', content):
        basename = m.group(1).replace(".lab", "")
        word = m.group(2).strip()
        if word and word != ".":
            basename_to_word[basename] = word

    audio_base = os.path.join(uaspeech_root, "audio", audio_subdir)
    # Speaker subfolder: audio/original/CF03/
    speaker_dir = os.path.join(audio_base, speaker_id)
    if not os.path.isdir(speaker_dir):
        speaker_dir = audio_base
    pairs = []
    for fname in sorted(os.listdir(speaker_dir))[: max_files * 3]:  # get more to match with MLF
        if not fname.lower().endswith(".wav"):
            continue
        basename = fname.replace(".wav", "")
        word = basename_to_word.get(basename)
        if not word:
            continue
        path = os.path.join(speaker_dir, fname)
        if os.path.isfile(path):
            pairs.append((path, word))
        if len(pairs) >= max_files:
            break
    return pairs


def run_one(wav_path: str, ground_truth: str, custom_vocab: list) -> dict:
    """Run 3-stage pipeline; return dict with transcripts and WER per stage."""
    try:
        baseline = baseline_asr(wav_path)
        personalized = personalized_asr(wav_path, custom_vocab)
        repaired = semantic_repair(personalized["transcript"], "")
    except Exception as e:
        return {"error": str(e), "wav": wav_path}
    ref = ground_truth.strip().upper()
    w_b = wer(ref, baseline["transcript"]) if ref else None
    w_p = wer(ref, personalized["transcript"]) if ref else None
    w_r = wer(ref, repaired) if ref else None
    return {
        "wav": os.path.basename(wav_path),
        "ground_truth": ground_truth,
        "baseline_transcript": baseline["transcript"],
        "personalized_transcript": personalized["transcript"],
        "repaired_transcript": repaired,
        "wer_baseline": w_b,
        "wer_personalized": w_p,
        "wer_repaired": w_r,
    }


def main():
    ap = argparse.ArgumentParser(description="Run verification tests on UA-Speech and generate report")
    ap.add_argument("--uaspeech_root", default=r"D:\research\data\UASpeech")
    ap.add_argument("--speaker", default="CF03", help="Speaker ID (e.g. CF03, M16)")
    ap.add_argument("--audio_subdir", default="original", choices=["original", "normalized", "noisereduce"])
    ap.add_argument("--max_files", type=int, default=10)
    ap.add_argument("--vocab_file", default=None, help="Path to vocab file (word:boost per line). If not set, uses first 100 words from MLF.")
    ap.add_argument("--output_dir", default=None, help="Report output dir (default: speech-adaptation-demo/reports)")
    args = ap.parse_args()

    uaspeech_root = os.path.abspath(args.uaspeech_root)
    if not os.path.isdir(uaspeech_root):
        print("UASpeech root not found:", uaspeech_root)
        sys.exit(1)

    pairs = find_speaker_wavs(uaspeech_root, args.speaker, args.audio_subdir, args.max_files)
    if not pairs:
        print("No (wav, word) pairs found for speaker", args.speaker)
        print("Check: mlf/%s/*_word.mlf and audio/%s/%s/*.wav" % (args.speaker, args.audio_subdir, args.speaker))
        sys.exit(1)

    # Build vocab: from file or from unique words in pairs
    if args.vocab_file and os.path.isfile(args.vocab_file):
        with open(args.vocab_file, "r", encoding="utf-8") as f:
            vocab_text = f.read()
        custom_vocab = parse_custom_vocab(vocab_text)
    else:
        words = list(dict.fromkeys(w for _, w in pairs))
        custom_vocab = [{"word": w, "boost": 1.5} for w in words]

    print("Running pipeline on %d files for speaker %s ..." % (len(pairs), args.speaker))
    results = []
    for wav_path, word in pairs:
        r = run_one(wav_path, word, custom_vocab)
        results.append(r)
        if "error" in r:
            print("  Error:", r["error"])
        else:
            print("  %s -> baseline WER=%.2f personalized=%.2f repaired=%.2f" % (
                r["wav"], r.get("wer_baseline") or 0, r.get("wer_personalized") or 0, r.get("wer_repaired") or 0))

    # Report
    out_dir = args.output_dir or os.path.join(DEMO_DIR, "reports")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(out_dir, "verification_report_%s_%s.md" % (args.speaker, ts))

    successful = [r for r in results if "error" not in r and r.get("wer_baseline") is not None]
    n = len(successful)
    if n == 0:
        avg_b, avg_p, avg_r = 0, 0, 0
    else:
        avg_b = sum(r["wer_baseline"] for r in successful) / n
        avg_p = sum(r["wer_personalized"] for r in successful) / n
        avg_r = sum(r["wer_repaired"] for r in successful) / n

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Pipeline Verification Report\n\n")
        f.write("**Date:** %s  \n" % datetime.now().isoformat())
        f.write("**Speaker:** %s  \n" % args.speaker)
        f.write("**UASpeech root:** %s  \n" % uaspeech_root)
        f.write("**Files tested:** %d (successful: %d)\n\n" % (len(results), n))
        f.write("## Summary\n\n")
        f.write("| Stage | Mean WER |\n|-------|----------|\n")
        f.write("| Baseline ASR | %.4f |\n" % avg_b)
        f.write("| Personalized ASR | %.4f |\n" % avg_p)
        f.write("| Semantic Repair | %.4f |\n\n" % avg_r)
        f.write("## Per-file results\n\n")
        f.write("| File | Ground Truth | Baseline WER | Personalized WER | Repaired WER |\n")
        f.write("|------|--------------|---------------|------------------|-------------|\n")
        for r in results:
            if "error" in r:
                f.write("| %s | - | ERROR | %s |\n" % (r.get("wav", ""), r["error"][:50]))
            else:
                f.write("| %s | %s | %.4f | %.4f | %.4f |\n" % (
                    r["wav"], r["ground_truth"], r.get("wer_baseline") or 0,
                    r.get("wer_personalized") or 0, r.get("wer_repaired") or 0))
        f.write("\n## Transcripts (first 3 files)\n\n")
        for r in successful[:3]:
            f.write("### %s (GT: %s)\n" % (r["wav"], r["ground_truth"]))
            f.write("- **Baseline:** %s\n" % r["baseline_transcript"])
            f.write("- **Personalized:** %s\n" % r["personalized_transcript"])
            f.write("- **Repaired:** %s\n\n" % r["repaired_transcript"])

    print("Report written to", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
