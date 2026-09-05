import io
import logging
import os
import tempfile
from typing import List, Tuple

import soundfile as sf
from pydub import AudioSegment

LOGGER = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a"}


def validate_audio_path(audio_path: str) -> None:
    if not audio_path or not os.path.exists(audio_path):
        raise FileNotFoundError("Audio file path is missing or does not exist.")

    ext = os.path.splitext(audio_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported audio format '{ext}'. Use WAV, MP3, FLAC, or M4A.")


def load_audio_bytes(audio_path: str) -> Tuple[bytes, str]:
    """
    Return audio bytes and a mime-like content type string.
    Tries soundfile first; if it fails, uses pydub to normalize to WAV.
    """
    validate_audio_path(audio_path)
    ext = os.path.splitext(audio_path)[1].lower()

    try:
        with sf.SoundFile(audio_path) as f:
            _ = f.frames  # Touch file to ensure it opens
        with open(audio_path, "rb") as f:
            return f.read(), f"audio/{ext.lstrip('.')}"
    except Exception as exc:
        LOGGER.warning("soundfile failed for %s, falling back to pydub: %s", audio_path, exc)

    audio = AudioSegment.from_file(audio_path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    audio.export(tmp_path, format="wav")

    try:
        with open(tmp_path, "rb") as f:
            return f.read(), "audio/wav"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            LOGGER.warning("Failed to delete temp file %s", tmp_path)


def parse_custom_vocab(text_block: str) -> List[dict]:
    """
    Parse lines like:
      Atorvastatin:2.0
      Calgary:1.5
    Returns a list of dicts with word + boost.
    """
    vocab = []
    if not text_block:
        return vocab

    for line in text_block.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            word, boost = line.split(":", 1)
            try:
                boost_val = float(boost.strip())
            except ValueError:
                boost_val = 1.5
        else:
            word = line
            boost_val = 1.5
        vocab.append({"word": word.strip(), "boost": boost_val})
    return vocab
