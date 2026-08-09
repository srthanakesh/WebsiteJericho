"""Local speech-to-text with faster-whisper."""

import io
import os
import threading

from faster_whisper import WhisperModel

_model = None
_lock = threading.Lock()


def _get_model() -> WhisperModel:
    global _model
    with _lock:
        if _model is None:
            size = os.getenv("WHISPER_MODEL", "small")
            _model = WhisperModel(size, device="cpu", compute_type="int8")
        return _model


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe an audio clip (any ffmpeg-decodable format, e.g. webm/ogg/wav)."""
    segments, _info = _get_model().transcribe(io.BytesIO(audio_bytes), vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()
