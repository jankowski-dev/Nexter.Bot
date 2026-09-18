"""
dispatcher.py — обработка входящих сообщений Viber.
"""

import notify
from logutil import ts


def handle_conversation_started() -> None:
    notify.send_viber_message("Привет! Я помогу отслеживать привычки и распорядок дня.")


def handle_message(text: str) -> None:
    t = text.strip()
    print(f"[DISPATCH] {ts()} text='{t}'")
    notify.send_viber_message("Бот работает в автоматическом режиме. Напоминания приходят по расписанию.")
