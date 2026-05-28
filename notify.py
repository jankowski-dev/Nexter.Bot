"""
notify.py — Отправка уведомлений в Viber через фоновую очередь.
Вебхук только ставит сообщение в очередь и сразу возвращает ответ.
Фоновый поток разбирает очередь и шлёт сообщения в Viber API.
"""

import os
import time
import queue
import threading
import requests
from datetime import datetime

_send_queue: queue.Queue = queue.Queue(maxsize=256)
_worker_started = False
_worker_lock = threading.Lock()


def _start_worker() -> None:
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
    t = threading.Thread(target=_send_worker, daemon=True, name="viber-sender")
    t.start()
    print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} 🔄 Фоновая очередь отправки запущена.")


def _send_worker() -> None:
    while True:
        try:
            item = _send_queue.get()
            if item is None:
                break
            payload, max_retries, retry_delay = item
            _send_payload_sync(payload, max_retries, retry_delay)
        except Exception:
            pass


def send_viber_message(text: str, max_retries: int = 2, retry_delay: int = 1) -> bool:
    _start_worker()
    try:
        _send_queue.put_nowait(({"receiver": None, "type": "text", "text": text}, max_retries, retry_delay))
    except queue.Full:
        print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Очередь переполнена, сообщение отброшено.")
        return False
    return True


def send_viber_keyboard(text: str, keyboard: dict = None, max_retries: int = 2, retry_delay: int = 1) -> bool:
    _start_worker()
    payload = {"receiver": None, "type": "text", "text": text, "min_api_version": 7}
    if keyboard:
        payload["keyboard"] = keyboard
    try:
        _send_queue.put_nowait((payload, max_retries, retry_delay))
    except queue.Full:
        print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Очередь переполнена, клавиатура отброшена.")
        return False
    return True


def _get_credentials() -> tuple[str | None, str | None]:
    return os.environ.get("VIBER_TOKEN"), os.environ.get("VIBER_USER_ID")


def _send_payload_sync(payload: dict, max_retries: int = 2, retry_delay: int = 1) -> bool:
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

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
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
