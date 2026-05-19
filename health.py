"""
health.py — Привычки: статистика, логика опроса.
"""

from survey_state import survey_state
from health_notion import get_habits_stats, update_all_counters
import keyboards as kb
import notify
import yaml
import os


_config: dict = {}


def load_config(path: str = "health_config.yaml") -> dict:
    global _config
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def show_stats() -> None:
    try:
        stats = get_habits_stats()
    except Exception:
        notify.send_viber_keyboard("⚠️ Не удалось загрузить статистику.", kb.reminder_keyboard())
        return

    if not stats:
        notify.send_viber_keyboard("Нет данных о привычках.", kb.reminder_keyboard())
        return

    habits = _config.get("habits", [])
    max_name = max((len(h) for h in habits), default=0)
    lines = ["📊 Статистика привычек", ""]
    for habit in habits:
        info = stats.get(habit, {})
        days = info.get("days_without", "—")
        days_str = str(days) if days != "" else "—"
        lines.append(f"{habit:<{max_name}} │ {days_str}")

    notify.send_viber_keyboard("\n".join(lines), kb.reminder_keyboard())


def start_survey() -> None:
    survey_state.start()
    habits = _config.get("habits", [])
    if not habits:
        notify.send_viber_keyboard("Нет привычек в конфигурации.", kb.reminder_keyboard())
        return
    notify.send_viber_keyboard("Давайте проведём ежедневный опрос")
    question = f"Вы употребляли «{habits[0].lower()}»?"
    notify.send_viber_keyboard(question, kb.survey_keyboard())


def handle_survey_answer(text: str, nav_callback) -> None:
    if text not in ("Да", "Нет"):
        return

    habits = _config.get("habits", [])
    relapsed = text == "Да"
    survey_state.answer(relapsed)

    if survey_state.is_complete(len(habits)):
        _finish_survey(nav_callback)
    else:
        next_habit = habits[survey_state.index]
        question = f"Вы употребляли «{next_habit.lower()}»?"
        notify.send_viber_keyboard(question, kb.survey_keyboard())


def _finish_survey(nav_callback) -> None:
    habits = _config.get("habits", [])
    try:
        stats = get_habits_stats()
    except Exception:
        survey_state.reset()
        notify.send_viber_keyboard("⚠️ Не удалось сохранить результаты.", kb.reminder_keyboard())
        nav_callback("reminder")
        return

    updates = {}
    for i, habit in enumerate(habits):
        updates[habit] = survey_state.answers.get(i, False)

    try:
        update_all_counters(updates, stats)
    except Exception:
        pass

    survey_state.reset()
    notify.send_viber_keyboard("✅ Опрос пройден!", kb.reminder_keyboard())
    nav_callback("reminder")
