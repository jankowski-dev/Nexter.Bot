"""audio_limits.py — согласованный с API предел размера аудио."""

import os

DEFAULT_MAX_AUDIO_MB = 8
MIN_MAX_AUDIO_MB = 1
MAX_MAX_AUDIO_MB = 20


def max_audio_mb() -> int:
    raw = (os.environ.get("MAX_AUDIO_MB") or "").strip()

    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_AUDIO_MB

    return min(MAX_MAX_AUDIO_MB, max(MIN_MAX_AUDIO_MB, value))


def max_audio_bytes() -> int:
    return max_audio_mb() * 1024 * 1024
