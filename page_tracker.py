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
