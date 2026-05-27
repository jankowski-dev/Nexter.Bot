"""
fasting.py — Интервальное голодание.
Хранит время последнего сброса (приёма пищи) и считает часы с того момента.
"""

from datetime import datetime

_start_time: datetime | None = None


def reset() -> float:
    """Сбросить счётчик (пользователь поел). Возвращает часы, прошедшие с предыдущего сброса."""
    global _start_time
    prev = hours()
    _start_time = datetime.now()
    return prev


def hours() -> float:
    """Сколько часов прошло с последнего сброса."""
    if _start_time is None:
        return 0.0
    delta = datetime.now() - _start_time
    return delta.total_seconds() / 3600.0


def is_active() -> bool:
    return _start_time is not None


def status() -> str:
    h = hours()
    if h < 1:
        return f"🍽 Голодание: {int(h * 60)} мин."
    return f"🍽 Голодание: {h:.1f} ч."
