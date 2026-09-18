"""
notion_webhook.py — приём и обработка вебхуков Notion.
События page.created фильтруются по базам Заявок/Отзывов, из страницы
достаётся поле «ID» и отправляется короткое уведомление в Viber.
"""

import hmac
import hashlib
import os
import requests
from datetime import datetime

import notify
import page_tracker

NOTION_API_VERSION = "2022-06-28"

_TRACKERS = {
    "claims": {
        "env": "CLAIMS_DB_ID",
        "label": "Получена новая заявка",
        "log_tag": "CLAIMS",
        "filter": {"property": "Статус", "select": {"equals": "Новая"}},
        "status_field": "Статус",
        "status_value": "Новая",
    },
    "reviews": {
        "env": "REVIEWS_DB_ID",
        "label": "Получен новый отзыв",
        "log_tag": "REVIEWS",
        "filter": None,
        "status_field": "",
        "status_value": "",
    },
}


def _normalize_id(value: str) -> str:
    return (value or "").replace("-", "").lower()


def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature)


def _tracker_for_parent(parent_id: str):
    norm = _normalize_id(parent_id)
    if not norm:
        return None, None
    for key, cfg in _TRACKERS.items():
        if _normalize_id(os.environ.get(cfg["env"], "")) == norm:
            return key, cfg
    return None, None


def _notion_headers() -> dict:
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
    }


def _fetch_page(page_id: str) -> dict | None:
    try:
        resp = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=_notion_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[NOTION-WH] ❌ Не удалось получить страницу {page_id[:8]}: {e}")
        return None


def _select_value(props: dict, field: str) -> str:
    sel = props.get(field, {}).get("select")
    return sel["name"] if sel else ""


def handle_event(payload: dict) -> bool:
    """Обрабатывает событие. True — отвечаем 200, False — нужен повтор доставки."""
    now = datetime.now().strftime("%H:%M:%S")

    if payload.get("type") != "page.created":
        return True

    entity = payload.get("entity") or {}
    page_id = entity.get("id", "")
    if not page_id:
        return True

    parent_id = ((payload.get("data") or {}).get("parent") or {}).get("id", "")
    state_key, cfg = _tracker_for_parent(parent_id)
    if not cfg:
        return True

    log_tag = cfg["log_tag"]
    db_id = os.environ.get(cfg["env"], "")

    page_tracker.ensure_warmed(db_id, state_key, log_tag, cfg["filter"], exclude=page_id)

    if page_tracker.already_notified(state_key, page_id):
        print(f"[{log_tag}] {now} ↩️ Дубликат события {page_id[:8]}")
        return True

    page = _fetch_page(page_id)
    if page is None:
        return False

    props = page.get("properties", {})
    if cfg["status_field"] and _select_value(props, cfg["status_field"]) != cfg["status_value"]:
        print(f"[{log_tag}] {now} ⏭️ Пропуск {page_id[:8]}: статус не «{cfg['status_value']}»")
        return True

    id_value = page_tracker.extract_id(props, "ID") or page_id[:8]
    if not notify.send_viber_message(f"{cfg['label']} {id_value}"):
        print(f"[{log_tag}] {now} ❌ Не отправлено: {cfg['label']} {id_value}")
        return False

    page_tracker.mark_notified(state_key, page_id)
    print(f"[{log_tag}] {now} ✅ Вебхук: {cfg['label']} {id_value}")
    return True
