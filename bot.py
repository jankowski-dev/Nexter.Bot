"""
bot.py — Точка входа.
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import sys
import yaml
import requests
from datetime import datetime
from waitress import serve

from app import app, PORT, TEST_SECRET
import notion_reader
import signal_tracker
import health_notion
import health
import notify
import keyboards as kb
from scheduler import start_scheduler


def _load_yaml(path: str) -> dict:
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

REQUIRED_ENV = ["VIBER_TOKEN", "VIBER_USER_ID", "NOTION_API_KEY"]

missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
if not os.environ.get("NOTION_API_KEY") and not os.environ.get("NOTION_TOKEN"):
    missing.append("NOTION_API_KEY или NOTION_TOKEN")
else:
    # Remove NOTION_API_KEY from missing if NOTION_TOKEN exists
    if "NOTION_API_KEY" in missing and os.environ.get("NOTION_TOKEN"):
        missing.remove("NOTION_API_KEY")

if missing:
    print(f"[STARTUP] ❌ КРИТИЧЕСКАЯ ОШИБКА: отсутствуют переменные: {', '.join(missing)}")
    print("[STARTUP] Завершение работы.")
    sys.exit(1)

print(f"[STARTUP] ✅ Все обязательные переменные заданы.")

if __name__ == "__main__":
    # Load crypto config
    crypto_cfg = notion_reader.load_config()

    # Load health configs
    health_notion.load_config()
    health.load_config()

    health_cfg = _load_yaml("health_config.yaml")

    print(f"[STARTUP] {datetime.now().strftime('%H:%M:%S')} 🚀 Запуск на порту {PORT}...")
    print(f"[STARTUP] Crypto DB: {crypto_cfg.get('notion', {}).get('database_id', 'не задан')}")
    print(f"[STARTUP] Health DB: {health_cfg.get('notion', {}).get('habits_db_id', 'не задан')}")
    print(f"[STARTUP] Schedule DB: {health_cfg.get('notion', {}).get('schedule_db_id', 'не задан')}")

    if TEST_SECRET:
        print(f"[STARTUP] 🔐 Тестовые эндпоинты защищены.")
    else:
        print(f"[STARTUP] ⚠️ TEST_SECRET не задан — тестовые эндпоинты открыты!")

    # Запуск планировщика
    start_scheduler()

    # Регистрация вебхука Viber
    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    viber_token = os.environ.get("VIBER_TOKEN", "").strip()
    print(f"[STARTUP] WEBHOOK_URL = '{webhook_url}'")
    print(f"[STARTUP] VIBER_TOKEN задан: {bool(viber_token)}")
    if webhook_url and viber_token:
        try:
            r = requests.post(
                "https://chatapi.viber.com/pa/set_webhook",
                headers={"X-Viber-Auth-Token": viber_token},
                json={"url": webhook_url, "event_types": ["message", "conversation_started", "delivered", "seen", "failed", "subscribed", "unsubscribed"]},
                timeout=15,
            )
            print(f"[STARTUP] Webhook HTTP {r.status_code}")
            print(f"[STARTUP] Webhook body: {r.text}")
        except Exception as e:
            print(f"[STARTUP] ⚠️ Webhook registration FAILED: {e}")
    else:
        print(f"[STARTUP] ❌❌❌ WEBHOOK_URL или VIBER_TOKEN не заданы — кнопки работать НЕ БУДУТ!")

    # Сразу шлём клавиатуру при старте
    notify.send_viber_keyboard("Бот запущен. Выбери раздел:", kb.root_keyboard())

    print(f"[STARTUP] 🌐 Waitress WSGI-сервер запущен (8 потоков).")
    serve(app, host="0.0.0.0", port=PORT, threads=8)
