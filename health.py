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

_QUESTIONS = {
    "Курение": "Вы сегодня курили?",
    "Алкоголь": "Вы сегодня употребляли алкоголь?",
    "Газировка": "Вы сегодня пили газировку?",
    "Сладости": "Вы сегодня ели сладости?",
    "Прогулка": "У вас сегодня была прогулка?",
    "Кофе": "Вы сегодня пили кофе?",
    "Переедание": "Вы сегодня переедали?",
    "Велотренировка": "У вас сегодня была велотренировка?",
    "Рутсам": "Вы сегодня занимались рутсамом?",
    "Мучное": "Вы сегодня ели мучное?",
    "Сахар": "Вы сегодня употребляли сахар?",
    "Английский": "Вы сегодня занимались английским?",
}

_ACHIEVEMENT = {"Прогулка", "Велотренировка", "Английский"}


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
    lines = ["📊 Статистика привычек", ""]
    for habit in habits:
        info = stats.get(habit, {})
        days = info.get("days_without", "—")
        days_str = str(days) if days != "" else "—"
        lines.append(f"  {days_str:>4}  ❘ {habit}")

    notify.send_viber_keyboard("\n".join(lines), kb.reminder_keyboard())


def _question(habit: str) -> str:
    return _QUESTIONS.get(habit, f"Вы сегодня соблюдали «{habit.lower()}»?")


def start_survey() -> None:
    survey_state.start()
    habits = _config.get("habits", [])
    if not habits:
        notify.send_viber_keyboard("Нет привычек в конфигурации.", kb.reminder_keyboard())
        return
    notify.send_viber_keyboard("Давайте проведём ежедневный опрос")
    notify.send_viber_keyboard(_question(habits[0]), kb.survey_keyboard())


def handle_survey_answer(text: str, nav_callback) -> None:
    if text not in ("Да", "Нет"):
        return

    habits = _config.get("habits", [])
    current = habits[survey_state.index]
    if current in _ACHIEVEMENT:
        relapsed = text == "Нет"
    else:
        relapsed = text == "Да"
    survey_state.answer(relapsed)

    if survey_state.is_complete(len(habits)):
        _finish_survey(nav_callback)
    else:
        next_habit = habits[survey_state.index]
        notify.send_viber_keyboard(_question(next_habit), kb.survey_keyboard())


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
