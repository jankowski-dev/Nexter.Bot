"""
page_tracker.py — состояние уведомлённых страниц Notion и извлечение поля ID.
Используется обработчиком вебхуков для дедупликации событий.
"""

import os
import json
import threading

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_notified_ids.json")
_state: dict[str, set[str]] = {}
_state_lock = threading.Lock()


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
    tmp_path = _STATE_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in _state.items()}, f)
        os.replace(tmp_path, _STATE_FILE)
    except Exception as e:
        if os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        print(f"[TRACKER] ❌ Ошибка сохранения состояния: {e}")


_load_state()


def _num_to_str(val) -> str:
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def _extract_id(props: dict, field: str) -> str:
    prop = props.get(field)
    if not prop:
        return ""
    ptype = prop.get("type", "")

    if ptype == "number":
        val = prop.get("number")
        return _num_to_str(val) if val is not None else ""
    if ptype in ("rich_text", "title"):
        arr = prop.get(ptype, [])
        return arr[0].get("plain_text", "") if arr else ""
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
        return _num_to_str(val)
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    return ""


def extract_id(props: dict, field: str) -> str:
    """Публичная обёртка над _extract_id."""
    return _extract_id(props, field)


def already_notified(state_key: str, page_id: str) -> bool:
    with _state_lock:
        return page_id in _state.get(state_key, set())


def mark_notified(state_key: str, page_id: str) -> None:
    with _state_lock:
        _state.setdefault(state_key, set()).add(page_id)
        _save_state()
