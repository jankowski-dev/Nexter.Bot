"""
reviews_tracker.py — Мониторинг новых отзывов в Notion.
Раз в час опрашивает БД и шлёт короткое уведомление "Получен новый отзыв <ID>".
"""

import os

import page_tracker

POLL_INTERVAL_MINUTES = 60


def check_new_reviews() -> None:
    page_tracker.poll_new_pages(
        db_id=os.environ.get("REVIEWS_DB_ID", ""),
        label="Получен новый отзыв",
        id_field="ID",
        state_key="reviews",
        log_tag="REVIEWS",
    )


def reset_state() -> None:
    page_tracker.reset_state("reviews")
