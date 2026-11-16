"""
transcriber.py — локальная расшифровка аудио через faster-whisper.
Модель загружается лениво и кэшируется в процессе.
"""

import os

from logutil import ts

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    from faster_whisper import WhisperModel

    name = os.environ.get("WHISPER_MODEL", "base")
    device = os.environ.get("WHISPER_DEVICE", "cpu")
    compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
    cache_dir = os.environ.get("WHISPER_CACHE_DIR", "/tmp/whisper")
    os.makedirs(cache_dir, exist_ok=True)
    print(f"[WHISPER] {ts()} Загрузка модели {name} ({device}/{compute_type})...")
    _MODEL = WhisperModel(name, device=device, compute_type=compute_type, download_root=cache_dir)
    print(f"[WHISPER] {ts()} Модель готова.")
    return _MODEL


def transcribe(path: str) -> tuple[str, int | None]:
    language = os.environ.get("WHISPER_LANGUAGE", "ru")
    model = _model()
    segments, info = model.transcribe(
        path,
        language=None if language == "auto" else language,
        vad_filter=True,
        beam_size=5,
    )
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
    duration = int(info.duration) if getattr(info, "duration", None) else None
    print(f"[WHISPER] {ts()} Расшифровано {len(text)} символов, {duration or '?'} сек.")
    return text, duration
