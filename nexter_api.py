"""
nexter_api.py — клиент API Nexter для задач и аудиозаметок.
"""

import base64
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


def _headers() -> dict:
    return {"Authorization": f"Bearer {bot_token()}"}


def fetch_upcoming(minutes: int = 5, timeout: int = 10) -> list[dict]:
    """Возвращает открытые задачи, срок которых наступит в ближайшие minutes минут."""
    token = bot_token()
    if not token:
        raise RuntimeError("NEXTER_BOT_TOKEN не задан")

    response = requests.get(
        f"{api_url()}/api/v1/bot/tasks/upcoming",
        params={"minutes": max(1, min(int(minutes), 60))},
        headers=_headers(),
        timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Nexter API HTTP {response.status_code}: {response.text[:200]}")

    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Nexter API вернул неожиданный ответ")

    print(f"[API] {ts()} Получено задач: {len(data)}")
    return data


def create_audio_note(
    *,
    viber_message_id: str,
    transcript: str,
    audio_bytes: bytes,
    audio_mime: str,
    audio_name: str,
    duration_seconds: int | None,
    timeout: int = 120,
) -> dict:
    if not configured():
        raise RuntimeError("Nexter API не настроен")

    data_url = f"data:{audio_mime};base64,{base64.b64encode(audio_bytes).decode('ascii')}"
    response = requests.post(
        f"{api_url()}/api/v1/bot/audio-notes",
        headers=_headers(),
        json={
            "viberMessageId": viber_message_id,
            "transcript": transcript,
            "audioMime": audio_mime,
            "audioName": audio_name,
            "audioSize": len(audio_bytes),
            "durationSeconds": duration_seconds,
            "audioDataUrl": data_url,
        },
        timeout=timeout,
    )
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"Nexter API HTTP {response.status_code}: {response.text[:300]}")

    payload = response.json()
    print(f"[API] {ts()} Аудиозаметка: status={payload.get('status')} note={payload.get('noteId')}")
    return payload
