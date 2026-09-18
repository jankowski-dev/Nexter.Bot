"""
logutil.py — вспомогательные функции логирования.
"""

from datetime import datetime


def ts() -> str:
    """Текущее время в формате ЧЧ:ММ:СС для логов."""
    return datetime.now().strftime("%H:%M:%S")
