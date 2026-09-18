"""
notion_webhook.py — приём и обработка вебхуков Notion.
События page.created фильтруются по базам Заявок/Отзывов, из страницы
достаётся поле «ID» и отправляется короткое уведомление в Viber.
"""

import hmac
import hashlib
import os

import notify
import notion_api
import page_tracker
from logutil import ts

_TRACKERS = {
    "claims": {
        "env": "CLAIMS_DB_ID",
        "label": "Получена заявка",
        "log_tag": "CLAIMS",
        "status_field": "Статус",
        "status_value": "Новая",
    },
    "reviews": {
        "env": "REVIEWS_DB_ID",
        "label": "Получен отзыв",
        "log_tag": "REVIEWS",
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


def _fetch_page(page_id: str) -> dict | None:
    try:
        return notion_api.get_page(page_id)
    except Exception as e:
        print(f"[NOTION-WH] {ts()} ❌ Не удалось получить страницу {page_id[:8]}: {e}")
        return None


def handle_event(payload: dict) -> bool:
    """Обрабатывает событие. True — отвечаем 200, False — нужен повтор доставки."""
    now = ts()

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

    if page_tracker.already_notified(state_key, page_id):
        print(f"[{log_tag}] {now} ↩️ Дубликат события {page_id[:8]}")
        return True

    page = _fetch_page(page_id)
    if page is None:
        return False

    props = page.get("properties", {})
    if cfg["status_field"] and notion_api.get_select(props, cfg["status_field"]) != cfg["status_value"]:
        print(f"[{log_tag}] {now} ⏭️ Пропуск {page_id[:8]}: статус не «{cfg['status_value']}»")
        return True

    id_value = notion_api.extract_id(props, "ID") or page_id[:8]
    message = f"[{id_value}] {cfg['label']}"
    if not notify.send_viber_message(message):
        print(f"[{log_tag}] {now} ❌ Не отправлено: {message}")
        return False

    page_tracker.mark_notified(state_key, page_id)
    print(f"[{log_tag}] {now} ✅ Вебхук: {message}")
    return True
