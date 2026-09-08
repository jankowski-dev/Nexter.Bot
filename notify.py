"""
notify.py — Отправка уведомлений в Viber через фоновую очередь.
Вебхук только ставит сообщение в очередь и сразу возвращает ответ.
Фоновый поток разбирает очередь и шлёт сообщения в Viber API.
"""

import io
import os
import time
import uuid
import queue
import threading
import requests
from datetime import datetime

_send_queue: queue.Queue = queue.Queue(maxsize=256)
_worker_started = False
_worker_lock = threading.Lock()

COMPRESS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_compressed_cache")
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 1920
JPEG_QUALITY = 80


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


def send_viber_image(image_url: str, text: str = "", max_retries: int = 2, retry_delay: int = 1) -> bool:
    _start_worker()
    payload = {"receiver": None, "type": "picture", "media": image_url}
    if text:
        payload["text"] = text
    try:
        _send_queue.put_nowait((payload, max_retries, retry_delay))
    except queue.Full:
        print(f"[NOTIFY] {datetime.now().strftime('%H:%M:%S')} ❌ Очередь переполнена, картинка отброшена.")
        return False
    return True


def _get_public_base() -> str:
    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    if webhook_url:
        return webhook_url.rsplit("/webhook", 1)[0]
    return ""


def compress_image(image_url: str) -> str:
    """Скачивает картинку, сжимает до 2MB если нужно, возвращает URL."""
    try:
        from PIL import Image
    except ImportError:
        print(f"[NOTIFY] Pillow не установлен — отправляю оригинал.")
        return image_url

    try:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[NOTIFY] ❌ Ошибка скачивания: {e}")
        return image_url

    original_size = len(resp.content)
    if original_size <= MAX_IMAGE_BYTES:
        print(f"[NOTIFY] Картинка {original_size // 1024}KB — OK")
        return image_url

    try:
        img = Image.open(io.BytesIO(resp.content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > MAX_DIMENSION:
            ratio = MAX_DIMENSION / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        compressed = buf.getvalue()
        compressed_size = len(compressed)

        print(f"[NOTIFY] Сжатие: {original_size // 1024}KB → {compressed_size // 1024}KB ({img.size[0]}x{img.size[1]})")

        os.makedirs(COMPRESS_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(COMPRESS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(compressed)

        base = _get_public_base()
        if not base:
            print(f"[NOTIFY] ⚠️ WEBHOOK_URL не задан — сжатая картинка недоступна.")
            return image_url

        file_url = f"{base}/compressed/{filename}"
        print(f"[NOTIFY] Сжатая картинка: {file_url}")
        return file_url

    except Exception as e:
        print(f"[NOTIFY] ❌ Ошибка сжатия: {e}")
        return image_url


def cleanup_compressed_cache() -> None:
    """Удаляет файлы старше 1 часа."""
    if not os.path.isdir(COMPRESS_DIR):
        return
    now = time.time()
    for f in os.listdir(COMPRESS_DIR):
        fp = os.path.join(COMPRESS_DIR, f)
        if os.path.isfile(fp) and now - os.path.getmtime(fp) > 3600:
            os.remove(fp)


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
