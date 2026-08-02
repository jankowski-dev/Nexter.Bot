"""
health.py — Привычки: статистика.
"""

from health_notion import get_habits_stats
import notify
import threading
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
    def _do():
        try:
            stats = get_habits_stats()
        except Exception:
            notify.send_viber_message("⚠️ Не удалось загрузить статистику.")
            return

        if not stats:
            notify.send_viber_message("Нет данных о привычках.")
            return

        habits = _config.get("habits", [])
        lines = ["📊 Статистика привычек", ""]
        for habit in habits:
            info = stats.get(habit, {})
            days = info.get("days_without", "—")
            days_str = str(days) if days != "" else "—"
            lines.append(f"  {days_str:>4}  ❘ {habit}")

        notify.send_viber_message("\n".join(lines))
    threading.Thread(target=_do, daemon=True).start()
