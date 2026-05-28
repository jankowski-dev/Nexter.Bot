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


def _matches(text: str, *keywords: str) -> bool:
    """Проверяет, содержит ли text любое из ключевых слов (без учёта регистра)."""
    t = text.lower()
    return any(kw in t for kw in keywords)


def handle_message(text: str) -> None:
    global _nav
    t = text.strip()
    t_lower = t.lower()
    print(f"[DISPATCH] {datetime.now().strftime('%H:%M:%S')} nav={_nav} text='{t}'")

    if _nav == Nav.SURVEY:
        from survey_state import survey_state as ss
        health.handle_survey_answer(t, _goto)
        if ss.active:
            return
        return

    if _nav == Nav.ROOT:
        if _matches(t, "crypto"):
            _nav = Nav.CRYPTO
            notify.send_viber_keyboard("💰 Crypto — отслеживание сделок:", kb.crypto_keyboard())
        elif _matches(t, "reminder"):
            _nav = Nav.REMINDER
            notify.send_viber_keyboard("🏥 Привычки и распорядок дня:", kb.reminder_keyboard())
        else:
            print(f"[DISPATCH] ROOT неизвестная кнопка: '{t}'")
            notify.send_viber_keyboard("Выбери раздел:", kb.root_keyboard())

    elif _nav == Nav.CRYPTO:
        if _matches(t, "отчет", "отчёт"):
            crypto.show_report()
        elif _matches(t, "статистика", "стат"):
            crypto.show_trade_stats()
        elif _matches(t, "назад"):
            _nav = Nav.ROOT
            notify.send_viber_keyboard("Выбери раздел:", kb.root_keyboard())
        else:
            print(f"[DISPATCH] CRYPTO неизвестная кнопка: '{t}'")
            notify.send_viber_keyboard("💰 Crypto — отслеживание сделок:", kb.crypto_keyboard())

    elif _nav == Nav.REMINDER:
        if _matches(t, "статистика", "стат"):
            health.show_stats()
        elif _matches(t, "внести", "данные"):
            _nav = Nav.SURVEY
            health.start_survey()
        elif _matches(t, "назад"):
            _nav = Nav.ROOT
            notify.send_viber_keyboard("Выбери раздел:", kb.root_keyboard())
        else:
            print(f"[DISPATCH] REMINDER неизвестная кнопка: '{t}'")
            notify.send_viber_keyboard("🏥 Привычки и распорядок дня:", kb.reminder_keyboard())


def _goto(state: str) -> None:
    global _nav
    _nav = state
