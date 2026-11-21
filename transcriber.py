"""
transcriber.py — локальная расшифровка аудио через faster-whisper.
Модель загружается лениво, кэшируется в процессе и выгружается после простоя.
"""

import gc
import os
import threading

from logutil import ts

_MODEL = None
_ACTIVE = 0
_UNLOAD_TIMER = None
_MODEL_LOCK = threading.RLock()
_TIMER_LOCK = threading.Lock()
_DEFAULT_IDLE_UNLOAD_SECONDS = 600


def idle_unload_seconds() -> int:
    raw = os.environ.get("WHISPER_IDLE_UNLOAD_SECONDS", str(_DEFAULT_IDLE_UNLOAD_SECONDS))
    try:
        seconds = int(raw.strip())
    except (TypeError, ValueError):
        return _DEFAULT_IDLE_UNLOAD_SECONDS
    return max(0, seconds)


def unload_model() -> bool:
    global _MODEL, _UNLOAD_TIMER
    with _MODEL_LOCK:
        with _TIMER_LOCK:
            _UNLOAD_TIMER = None
        if _MODEL is None:
            return False
        if _ACTIVE > 0:
            return False
        _MODEL = None
    gc.collect()
    print(f"[WHISPER] {ts()} Модель выгружена после простоя.")
    return True


def _cancel_unload() -> None:
    global _UNLOAD_TIMER
    with _TIMER_LOCK:
        if _UNLOAD_TIMER is not None:
            _UNLOAD_TIMER.cancel()
            _UNLOAD_TIMER = None


def _schedule_unload() -> None:
    global _UNLOAD_TIMER
    seconds = idle_unload_seconds()
    if seconds <= 0:
        return
    with _TIMER_LOCK:
        if _UNLOAD_TIMER is not None:
            _UNLOAD_TIMER.cancel()
        timer = threading.Timer(seconds, unload_model)
        timer.daemon = True
        _UNLOAD_TIMER = timer
        timer.start()


def _model():
    global _MODEL
    with _MODEL_LOCK:
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
    global _ACTIVE
    language = os.environ.get("WHISPER_LANGUAGE", "ru")
    _cancel_unload()
    with _MODEL_LOCK:
        _ACTIVE += 1
    try:
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
    finally:
        with _MODEL_LOCK:
            _ACTIVE -= 1
        _schedule_unload()
