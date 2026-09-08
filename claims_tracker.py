"""
claims_tracker.py — Мониторинг новых заявок в Notion.
Каждые N минут опрашивает БД, при новой заявке шлёт уведомление в Viber.
"""

import os
import requests
from datetime import datetime

import notify

NOTION_API_VERSION = "2022-06-28"

_notified_ids: set[str] = set()

POLL_INTERVAL_MINUTES = 1


def _notion_headers() -> dict:
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def _get_title(props: dict, field: str) -> str:
    arr = props.get(field, {}).get("title", [])
    return arr[0]["plain_text"] if arr else ""


def _get_text(props: dict, field: str) -> str:
    arr = props.get(field, {}).get("rich_text", [])
    return arr[0]["plain_text"] if arr else ""


def _get_select(props: dict, field: str) -> str:
    sel = props.get(field, {}).get("select")
    return sel["name"] if sel else ""


def _get_phone(props: dict, field: str) -> str:
    return props.get(field, {}).get("phone_number", "") or ""


def _get_checkbox(props: dict, field: str) -> bool:
    return props.get(field, {}).get("checkbox", False)


def _get_date(props: dict, field: str) -> str:
    date_obj = props.get(field, {}).get("date")
    if not date_obj:
        return ""
    start = date_obj.get("start", "")
    if not start:
        return ""
    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return start


def _format_message(props: dict) -> str:
    name = _get_title(props, "Имя") or "без имени"
    phone = _get_phone(props, "Телефон")
    address = _get_text(props, "Адрес")
    service = _get_select(props, "Услуга")
    source = _get_select(props, "Источник")
    reception = _get_date(props, "Прием")
    description = _get_text(props, "Описание")
    urgent = _get_checkbox(props, "Срочный вызов")
    outside_city = _get_checkbox(props, "За городом")
    materials = _get_checkbox(props, "Закупка материалов")

    flags = []
    if urgent:
        flags.append("🚨 Срочно")
    if outside_city:
        flags.append("📍 За городом")
    if materials:
        flags.append("🛒 Закупка материалов")

    lines = [
        "📋 Новая заявка",
        "",
        f"👤 {name}",
    ]

    if phone:
        lines.append(f"📞 {phone}")
    if address:
        lines.append(f"🏠 {address}")
    if service:
        lines.append(f"🔧 {service}")
    if source:
        lines.append(f"📡 Источник: {source}")
    if reception:
        lines.append(f"📅 Приём: {reception}")
    if description:
        lines.append(f"📝 {description}")
    if flags:
        lines.append("")
        lines.append(" | ".join(flags))

    return "\n".join(lines)


def check_new_claims() -> None:
    """Опрашивает БД заявок и шлёт уведомления о новых."""
    database_id = os.environ.get("CLAIMS_DB_ID", "")
    if not database_id:
        return

    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    if not api_key:
        print(f"[CLAIMS] {datetime.now().strftime('%H:%M:%S')} ❌ NOTION_API_KEY не задан.")
        return

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = _notion_headers()

    try:
        response = requests.post(
            url,
            headers=headers,
            json={
                "page_size": 100,
                "filter": {
                    "property": "Статус",
                    "select": {"equals": "Новая"},
                },
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        body = response.text[:300] if response is not None else ""
        print(f"[CLAIMS] {datetime.now().strftime('%H:%M:%S')} ❌ HTTP {response.status_code}: {body}")
        return
    except Exception as e:
        print(f"[CLAIMS] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка запроса: {e}")
        return

    results = data.get("results", [])
    new_count = 0

    for page in results:
        page_id = page.get("id", "")
        if page_id in _notified_ids:
            continue

        _notified_ids.add(page_id)
        new_count += 1

        props = page.get("properties", {})
        message = _format_message(props)
        notify.send_viber_message(message)
        print(f"[CLAIMS] {datetime.now().strftime('%H:%M:%S')} ✅ Уведомление: {_get_title(props, 'Имя') or page_id[:8]}")

    if new_count == 0 and results:
        pass
    elif new_count == 0:
        print(f"[CLAIMS] {datetime.now().strftime('%H:%M:%S')} — новых заявок нет.")


def reset_state() -> None:
    """Сбрасывает список уведомлённых (для тестов)."""
    global _notified_ids
    _notified_ids = set()
