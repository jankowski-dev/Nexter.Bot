"""
dispatcher.py — Маршрутизация команд Viber и состояние навигации.
"""

from datetime import datetime
import notify
import keyboards as kb
import crypto
import health


class Nav:
    ROOT = "root"
    CRYPTO = "crypto"
    REMINDER = "reminder"
    SURVEY = "survey"


_nav = Nav.ROOT


def get_nav() -> str:
    return _nav


def set_nav(state: str) -> None:
    global _nav
    _nav = state


def handle_conversation_started() -> None:
    global _nav
    _nav = Nav.ROOT
    notify.send_viber_keyboard(
        "Привет! Я помогу отслеживать крипто-сделки и полезные привычки.\nВыбери раздел:",
        kb.root_keyboard(),
    )


def handle_message(text: str) -> None:
    global _nav
    print(f"[DISPATCH] {datetime.now().strftime('%H:%M:%S')} nav={_nav} text='{text}'")

    t = text.strip()

    if _nav == Nav.SURVEY:
        from survey_state import survey_state as ss
        health.handle_survey_answer(t, _goto)
        if ss.active:
            return
        return

    if _nav == Nav.ROOT:
        if t == "Crypto":
            _nav = Nav.CRYPTO
            notify.send_viber_keyboard("💰 Crypto — отслеживание сделок:", kb.crypto_keyboard())
        elif t == "Reminder":
            _nav = Nav.REMINDER
            notify.send_viber_keyboard("🏥 Привычки и распорядок дня:", kb.reminder_keyboard())
        else:
            notify.send_viber_keyboard("Выбери раздел:", kb.root_keyboard())

    elif _nav == Nav.CRYPTO:
        if t == "Текущий отчет":
            crypto.show_report()
        elif t == "Статистика":
            crypto.show_trade_stats()
        elif t == "Назад":
            _nav = Nav.ROOT
            notify.send_viber_keyboard("Выбери раздел:", kb.root_keyboard())

    elif _nav == Nav.REMINDER:
        if t == "Статистика":
            health.show_stats()
        elif t == "Внести данные":
            _nav = Nav.SURVEY
            health.start_survey()
        elif t == "Назад":
            _nav = Nav.ROOT
            notify.send_viber_keyboard("Выбери раздел:", kb.root_keyboard())


def _goto(state: str) -> None:
    global _nav
    _nav = state
