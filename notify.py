"""
notify.py — Отправка уведомлений в Viber.
Использует VIBER_TOKEN и VIBER_USER_ID из переменных окружения.
С retry-логикой: до 3 попыток с паузой 5 секунд.
"""

import os
import hashlib
import time
import requests
from datetime import datetime

_SENT_HASHES: dict[str, float] = {}
_DEDUP_WINDOW_SEC = 10


def _get_credentials() -> tuple[str | None, str | None]:
    return os.environ.get("VIBER_TOKEN"), os.environ.get("VIBER_USER_ID")


def send_viber_message(text: str, max_retries: int = 3, retry_delay: int = 5) -> bool:
    return _send_payload({"receiver": None, "type": "text", "text": text},
                         max_retries, retry_delay)


def send_viber_keyboard(text: str, keyboard: dict = None, max_retries: int = 3, retry_delay: int = 5) -> bool:
    payload = {"receiver": None, "type": "text", "text": text, "min_api_version": 7}
    if keyboard:
        payload["keyboard"] = keyboard
    return _send_payload(payload, max_retries, retry_delay)


def _send_payload(payload: dict, max_retries: int = 3, retry_delay: int = 5) -> bool:
    viber_token, user_id = _get_credentials()

    if not viber_token:
        print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ VIBER_TOKEN не задан — отправка невозможна.")
        return False

    if not user_id:
        print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ VIBER_USER_ID не задан — отправка невозможна.")
        return False

    payload["receiver"] = user_id

    url = "https://chatapi.viber.com/pa/send_message"
    headers = {
        "X-Viber-Auth-Token": viber_token,
        "Content-Type": "application/json"
    }

    text_preview = payload.get("text", "")[:100].replace("\n", " ")

    msg_hash = hashlib.new("md5", payload.get("text", "").encode(), usedforsecurity=False).hexdigest()
    now = time.time()
    for h in list(_SENT_HASHES.keys()):
        if now - _SENT_HASHES[h] > _DEDUP_WINDOW_SEC:
            del _SENT_HASHES[h]
    if msg_hash in _SENT_HASHES:
        return True

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                _SENT_HASHES[msg_hash] = now
                print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ✅ Отправлено: {text_preview}...")
                return True
            else:
                print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ HTTP {response.status_code}: {response.text[:200]}")

        except requests.exceptions.Timeout:
            print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Таймаут (попытка {attempt}/{max_retries}).")
        except requests.exceptions.RequestException as e:
            print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка сети: {e}")
        except Exception as e:
            print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка: {e}")

        if attempt < max_retries:
            time.sleep(retry_delay)

    print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Все {max_retries} попыток не удались.")
    return False
