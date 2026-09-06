"""
dispatcher.py — Обработка входящих сообщений Viber.
"""

from datetime import datetime
import notify


def handle_conversation_started() -> None:
    notify.send_viber_message("Привет! Я помогу отслеживать привычки и распорядок дня.")


def handle_message(text: str) -> None:
    t = text.strip()
    print(f"[DISPATCH] {datetime.now().strftime('%H:%M:%S')} text='{t}'")
    notify.send_viber_message("Бот работает в автоматическом режиме. Напоминания приходят по расписанию.")
