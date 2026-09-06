"""
bot.py — Точка входа.
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import requests
from datetime import datetime
from waitress import serve

from app import app, PORT, TEST_SECRET
import health_notion
import notify
from scheduler import start_scheduler


REQUIRED_ENV = ["VIBER_TOKEN", "VIBER_USER_ID", "NOTION_API_KEY"]

missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
if not os.environ.get("NOTION_API_KEY") and not os.environ.get("NOTION_TOKEN"):
    missing.append("NOTION_API_KEY или NOTION_TOKEN")
else:
    if "NOTION_API_KEY" in missing and os.environ.get("NOTION_TOKEN"):
        missing.remove("NOTION_API_KEY")

if missing:
    print(f"[STARTUP] ❌ КРИТИЧЕСКАЯ ОШИБКА: отсутствуют переменные: {', '.join(missing)}")
    print("[STARTUP] Завершение работы.")
    sys.exit(1)

print(f"[STARTUP] ✅ Все обязательные переменные заданы.")

if __name__ == "__main__":
    health_notion.load_config()

    print(f"[STARTUP] {datetime.now().strftime('%H:%M:%S')} 🚀 Запуск на порту {PORT}...")

    if TEST_SECRET:
        print(f"[STARTUP] 🔐 Тестовые эндпоинты защищены.")
    else:
        print(f"[STARTUP] ⚠️ TEST_SECRET не задан — тестовые эндпоинты открыты!")

    start_scheduler()

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

    notify.send_viber_message("Бот запущен.")

    print(f"[STARTUP] 🌐 Waitress WSGI-сервер запущен (8 потоков).")
    serve(app, host="0.0.0.0", port=PORT, threads=8)
