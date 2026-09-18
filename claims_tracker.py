"""
claims_tracker.py — Мониторинг новых заявок в Notion.
Каждые N минут опрашивает БД и шлёт короткое уведомление "Получена новая заявка <ID>".
"""

import os

import page_tracker

POLL_INTERVAL_MINUTES = 10


def check_new_claims() -> None:
    page_tracker.poll_new_pages(
        db_id=os.environ.get("CLAIMS_DB_ID", ""),
        label="Получена новая заявка",
        id_field="ID",
        state_key="claims",
        log_tag="CLAIMS",
        filter={"property": "Статус", "select": {"equals": "Новая"}},
    )


def reset_state() -> None:
    page_tracker.reset_state("claims")
