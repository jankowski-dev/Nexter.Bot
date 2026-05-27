"""
fasting.py — Интервальное голодание.
Хранит время последнего сброса (приёма пищи) и считает часы с того момента.
"""

from datetime import datetime

_start_time: datetime | None = None


def start() -> None:
    """Запустить счётчик (если ещё не запущен)."""
    global _start_time
    if _start_time is None:
        _start_time = datetime.now()


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


def minutes() -> float:
    """Сколько минут прошло с последнего сброса."""
    return hours() * 60.0


def status() -> str:
    m = minutes()
    if m < 1:
        return f"🍽 Голодание: 0 мин."
    return f"🍽 Голодание: {int(m)} мин."
