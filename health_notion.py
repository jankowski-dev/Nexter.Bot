"""
health_notion.py — Notion API для привычек и распорядка дня.
Конфигурация из health_config.yaml, API-ключ из VIBER_TOKEN окружения.
"""

import os
import yaml
import requests
from datetime import datetime
from typing import Optional

NOTION_API_VERSION = "2022-06-28"

_config: dict = {}


def load_config(path: str = "health_config.yaml") -> dict:
    global _config
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def _notion_headers() -> dict:
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def _get_title(props: dict, field_name: str) -> str:
    title_arr = props.get(field_name, {}).get("title", [])
    return title_arr[0]["plain_text"] if title_arr else ""


def _get_formula_value(props: dict, field_name: str):
    formula = props.get(field_name, {}).get("formula", {})
    if not formula:
        return ""
    return formula.get("number", formula.get("string", ""))


def _get_number(props: dict, field_name: str) -> float:
    return props.get(field_name, {}).get("number", 0) or 0


def _get_rich_text(props: dict, field_name: str) -> str:
    rt_arr = props.get(field_name, {}).get("rich_text", [])
    return rt_arr[0]["plain_text"] if rt_arr else ""


def get_habits_stats() -> dict:
    database_id = _config.get("notion", {}).get("habits_db_id", "")
    fields_cfg = _config.get("habits_fields", {})
    name_field = fields_cfg.get("name", "Название")
    days_field = fields_cfg.get("days_without", "Дней без")
    counter_field = fields_cfg.get("counter", "Счетчик")
    habits_list = _config.get("habits", [])

    if not database_id:
        print(f"[HEALTH_NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ habits_db_id не задан.")
        return {}

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = _notion_headers()

    try:
        response = requests.post(url, headers=headers, json={"page_size": 100}, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception:
        print(f"[HEALTH_NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка запроса привычек.")
        return {}

    result = {}
    for page in data.get("results", []):
        props = page.get("properties", {})
        title = _get_title(props, name_field)
        if title.lower() in [h.lower() for h in habits_list]:
            result[title] = {
                "days_without": _get_formula_value(props, days_field),
                "counter": _get_number(props, counter_field),
                "page_id": page["id"],
            }
    return result


def update_all_counters(updates: dict, stats: dict) -> None:
    counter_field = _config.get("habits_fields", {}).get("counter", "Счетчик")
    headers = _notion_headers()

    for name, relapsed in updates.items():
        info = stats.get(name)
        if not info:
            continue
        new_counter = 0 if relapsed else info["counter"] + 1
        try:
            resp = requests.patch(
                f"https://api.notion.com/v1/pages/{info['page_id']}",
                headers=headers,
                json={"properties": {counter_field: {"number": new_counter}}},
                timeout=15,
            )
            resp.raise_for_status()
        except Exception:
            print(f"[HEALTH_NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка обновления счётчика для {name}.")


def get_schedule() -> list[dict]:
    database_id = _config.get("notion", {}).get("schedule_db_id", "")
    fields_cfg = _config.get("schedule_fields", {})
    name_field = fields_cfg.get("name", "Название").strip()
    time_field_hint = fields_cfg.get("time", "Время").strip()

    if not database_id:
        print(f"[HEALTH_NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ schedule_db_id не задан.")
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = _notion_headers()

    payload: dict = {"page_size": 100}

    try:
        # Первый запрос без фильтра — чтобы узнать имена полей
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception:
        print(f"[HEALTH_NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка запроса расписания.")
        return []

    results = data.get("results", [])
    actual_time_field = time_field_hint
    date_field = ""

    if results:
        sample_props = results[0].get("properties", {})
        for pname, pval in sample_props.items():
            ptype = pval.get("type", "")
            if time_field_hint.lower() in pname.lower() and ptype in ("rich_text", "title"):
                actual_time_field = pname
            if ("дата" in pname.lower() or "date" in pname.lower()) and ptype == "date":
                date_field = pname

    # Если нашли поле даты, фильтруем по сегодня
    if date_field:
        payload["filter"] = {
            "property": date_field,
            "date": {"equals": today},
        }
        print(f"[HEALTH_NOTION] Фильтр по дате: {date_field} = {today}")
        results = []
        has_more = True
        start_cursor = None
        try:
            while has_more:
                if start_cursor:
                    payload["start_cursor"] = start_cursor
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                results.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
        except Exception:
            print(f"[HEALTH_NOTION] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка запроса с фильтром.")
            return []

    if actual_time_field != time_field_hint:
        print(f"[HEALTH_NOTION] Поле времени: '{actual_time_field}'")

    items = []
    for page in results:
        props = page.get("properties", {})
        name = _get_title(props, name_field) or _get_rich_text(props, name_field)
        time_val = _get_rich_text(props, actual_time_field) or _get_title(props, actual_time_field)
        time_val = time_val.strip()
        if name and time_val:
            items.append({"name": name, "time": time_val})
    return items
