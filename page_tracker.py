"""
page_tracker.py — Универсальный мониторинг новых страниц в базах Notion.
Хранит множество уведомлённых page_id по каждому трекеру и шлёт короткое
сообщение "<label> <ID>" при появлении новой страницы.
"""

import os
import json
import requests
from datetime import datetime

import notify

NOTION_API_VERSION = "2022-06-28"

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_notified_ids.json")
_state: dict[str, set[str]] = {}


def _load_state() -> None:
    global _state
    if not os.path.isfile(_STATE_FILE):
        _state = {}
        return
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            _state = {k: set(v) for k, v in raw.items()}
        elif isinstance(raw, list):
            _state = {"claims": set(raw)}
        else:
            _state = {}
        total = sum(len(v) for v in _state.values())
        print(f"[TRACKER] Загружено {total} ID из кэша.")
    except Exception:
        _state = {}


def _save_state() -> None:
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in _state.items()}, f)
    except Exception as e:
        print(f"[TRACKER] ❌ Ошибка сохранения состояния: {e}")


_load_state()


def _notion_headers() -> dict:
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def _extract_id(props: dict, field: str) -> str:
    prop = props.get(field)
    if not prop:
        return ""
    ptype = prop.get("type", "")

    if ptype == "number":
        val = prop.get("number")
        return str(int(val)) if val is not None else ""
    if ptype in ("rich_text", "title"):
        arr = prop.get(ptype, [])
        return arr[0]["plain_text"] if arr else ""
    if ptype == "unique_id":
        uid = prop.get("unique_id") or {}
        number = uid.get("number")
        if number is None:
            return ""
        prefix = uid.get("prefix")
        return f"{prefix}-{number}" if prefix else str(number)
    if ptype == "formula":
        formula = prop.get("formula") or {}
        ftype = formula.get("type", "")
        val = formula.get(ftype)
        if val is None:
            return ""
        if ftype == "number":
            return str(int(val))
        return str(val)
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    return ""


def _query_pages(db_id: str, filter: dict | None) -> list[dict]:
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = _notion_headers()
    pages: list[dict] = []
    payload: dict = {"page_size": 100}
    if filter:
        payload["filter"] = filter

    while True:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return pages


def poll_new_pages(
    db_id: str,
    label: str,
    id_field: str,
    state_key: str,
    log_tag: str,
    filter: dict | None = None,
) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    if not db_id:
        return

    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    if not api_key:
        print(f"[{log_tag}] {now} ❌ NOTION_API_KEY не задан.")
        return

    try:
        pages = _query_pages(db_id, filter)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        body = e.response.text[:300] if e.response is not None else ""
        print(f"[{log_tag}] {now} ❌ HTTP {status}: {body}")
        return
    except Exception as e:
        print(f"[{log_tag}] {now} ❌ Ошибка запроса: {e}")
        return

    if state_key not in _state:
        known = set()
        for page in pages:
            page_id = page.get("id", "")
            if page_id:
                known.add(page_id)
        _state[state_key] = known
        _save_state()
        print(f"[{log_tag}] {now} 🌱 Первый запуск: прогрето {len(known)} ID без отправки.")
        return

    known = _state[state_key]
    new_count = 0
    for page in pages:
        page_id = page.get("id", "")
        if not page_id or page_id in known:
            continue
        known.add(page_id)
        _save_state()
        new_count += 1
        props = page.get("properties", {})
        id_value = _extract_id(props, id_field) or page_id[:8]
        notify.send_viber_message(f"{label} {id_value}")
        print(f"[{log_tag}] {now} ✅ Уведомление: {label} {id_value}")

    if new_count:
        print(f"[{log_tag}] {now} ✅ Новых: {new_count}")
    else:
        print(f"[{log_tag}] {now} — новых нет.")


def reset_state(state_key: str) -> None:
    """Сбрасывает набор уведомлённых для трекера (для тестов)."""
    _state[state_key] = set()
    _save_state()
