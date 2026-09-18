"""
health_notion.py — Notion API для привычек и распорядка дня.
Конфигурация из health_config.yaml.
"""

import os
from datetime import datetime

import notion_api
from logutil import ts

_config: dict = {}


def load_config(path: str = "health_config.yaml") -> dict:
    import yaml
    global _config
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def increment_all_habit_counters() -> None:
    """Каждый день в 22:00 увеличивает счётчик всех привычек на 1."""
    database_id = _config.get("notion", {}).get("habits_db_id", "")
    counter_field = _config.get("habits_fields", {}).get("counter", "Счетчик")
    habits_list = _config.get("habits", [])
    name_field = _config.get("habits_fields", {}).get("name", "Название")

    if not database_id or not habits_list:
        print(f"[HEALTH_NOTION] {ts()} ❌ habits не настроены.")
        return

    try:
        pages = notion_api.query_database(database_id)
    except Exception:
        print(f"[HEALTH_NOTION] {ts()} ❌ Ошибка запроса привычек.")
        return

    habits_lower = [h.lower() for h in habits_list]
    updated = 0
    for page in pages:
        props = page.get("properties", {})
        title = notion_api.get_title(props, name_field)
        if title.lower() not in habits_lower:
            continue
        new_counter = int(notion_api.get_number(props, counter_field)) + 1
        try:
            notion_api.update_page(page["id"], {counter_field: {"number": new_counter}})
            updated += 1
        except Exception:
            print(f"[HEALTH_NOTION] {ts()} ❌ Ошибка +1 для {title}.")

    print(f"[HEALTH_NOTION] {ts()} ✅ +1 к {updated} привычкам.")


def get_schedule() -> list[dict]:
    database_id = _config.get("notion", {}).get("schedule_db_id", "")
    fields_cfg = _config.get("schedule_fields", {})
    name_field = fields_cfg.get("name", "Название").strip()
    time_field_hint = fields_cfg.get("time", "Время").strip()

    if not database_id:
        print(f"[HEALTH_NOTION] {ts()} ❌ schedule_db_id не задан.")
        return []

    try:
        results = notion_api.query_database(database_id)
    except Exception:
        print(f"[HEALTH_NOTION] {ts()} ❌ Ошибка запроса расписания.")
        return []

    actual_time_field = time_field_hint
    date_field = ""
    if results:
        for pname, pval in results[0].get("properties", {}).items():
            ptype = pval.get("type", "")
            if time_field_hint.lower() in pname.lower() and ptype in ("rich_text", "title"):
                actual_time_field = pname
            if ("дата" in pname.lower() or "date" in pname.lower()) and ptype == "date":
                date_field = pname

    if date_field:
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"[HEALTH_NOTION] Фильтр по дате: {date_field} = {today}")
        try:
            results = notion_api.query_database(
                database_id, filter={"property": date_field, "date": {"equals": today}}
            )
        except Exception:
            print(f"[HEALTH_NOTION] {ts()} ❌ Ошибка запроса с фильтром.")
            return []

    if actual_time_field != time_field_hint:
        print(f"[HEALTH_NOTION] Поле времени: '{actual_time_field}'")

    items = []
    for page in results:
        props = page.get("properties", {})
        name = notion_api.get_title(props, name_field) or notion_api.get_rich_text(props, name_field)
        time_val = notion_api.get_rich_text(props, actual_time_field) or notion_api.get_title(props, actual_time_field)
        time_val = time_val.strip()
        if name and time_val:
            items.append({"name": name, "time": time_val})
    return items
