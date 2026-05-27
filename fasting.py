"""
fasting.py — Интервальное голодание.
Хранит время последнего сброса (приёма пищи) и считает часы с того момента.
"""

from datetime import datetime, timedelta

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
    try:
        from health_notion import set_fasting_counter
        set_fasting_counter(0)
    except Exception:
        pass
    return prev


def hours() -> float:
    """Сколько часов прошло с последнего сброса."""
    if _start_time is None:
        return 0.0
    delta = datetime.now() - _start_time
    return delta.total_seconds() / 3600.0


def is_active() -> bool:
    return _start_time is not None


def init_from_notion(hours_val: int) -> None:
    """Восстановить _start_time из сохранённого в Notion значения (в часах)."""
    global _start_time
    if hours_val > 0:
        _start_time = datetime.now() - timedelta(hours=hours_val)


def status() -> str:
    h = hours()
    if h < 1:
        return f"🍽 Голодание: 0 ч."
    return f"🍽 Голодание: {int(h)} ч."
