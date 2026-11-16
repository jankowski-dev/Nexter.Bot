"""
nexter_api.py — клиент API Nexter для чтения ближайших задач.
"""

import os

import requests

from logutil import ts

DEFAULT_API_URL = "https://nexterapi-production.up.railway.app"


def api_url() -> str:
    return (os.environ.get("NEXTER_API_URL") or DEFAULT_API_URL).rstrip("/")


def bot_token() -> str:
    return (os.environ.get("NEXTER_BOT_TOKEN") or "").strip()


def configured() -> bool:
    return bool(api_url() and bot_token())


def fetch_upcoming(minutes: int = 5, timeout: int = 10) -> list[dict]:
    """Возвращает открытые задачи, срок которых наступит в ближайшие minutes минут."""
    token = bot_token()
    if not token:
        raise RuntimeError("NEXTER_BOT_TOKEN не задан")

    response = requests.get(
        f"{api_url()}/api/v1/bot/tasks/upcoming",
        params={"minutes": max(1, min(int(minutes), 60))},
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Nexter API HTTP {response.status_code}: {response.text[:200]}"
        )

    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Nexter API вернул неожиданный ответ")

    print(f"[API] {ts()} Получено задач: {len(data)}")
    return data
