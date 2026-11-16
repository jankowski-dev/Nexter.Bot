"""
bot.py — точка входа Nexter.Bot.
"""

import os
import sys
from datetime import datetime

import requests
from waitress import serve

sys.stdout.reconfigure(line_buffering=True)

from app import PORT, TEST_SECRET, app
from scheduler import start_scheduler

missing = []
if not os.environ.get("VIBER_TOKEN"):
    missing.append("VIBER_TOKEN")
if not os.environ.get("VIBER_USER_ID"):
    missing.append("VIBER_USER_ID")
if not (os.environ.get("NEXTER_BOT_TOKEN") or "").strip():
    missing.append("NEXTER_BOT_TOKEN")

if missing:
    print(f"[STARTUP] ❌ Отсутствуют переменные: {', '.join(missing)}")
    sys.exit(1)

print("[STARTUP] ✅ Обязательные переменные заданы.")
print(f"[STARTUP] Nexter API: {os.environ.get('NEXTER_API_URL') or 'https://nexterapi-production.up.railway.app'}")


def _register_webhook() -> None:
    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    viber_token = os.environ.get("VIBER_TOKEN", "").strip()
    if not webhook_url or not viber_token:
        print("[STARTUP] ⚠️ WEBHOOK_URL не задан — входящие сообщения Viber отключены.")
        return
    try:
        response = requests.post(
            "https://chatapi.viber.com/pa/set_webhook",
            headers={"X-Viber-Auth-Token": viber_token},
            json={
                "url": webhook_url,
                "event_types": ["message", "conversation_started", "delivered", "seen", "failed"],
            },
            timeout=15,
        )
        print(f"[STARTUP] Webhook HTTP {response.status_code}")
    except Exception as error:
        print(f"[STARTUP] ⚠️ Webhook registration failed: {error}")


if __name__ == "__main__":
    print(f"[STARTUP] {datetime.now().strftime('%H:%M:%S')} 🚀 Запуск на порту {PORT}...")
    if not TEST_SECRET:
        print("[STARTUP] ⚠️ TEST_SECRET не задан — тестовые эндпоинты отключены.")
    _register_webhook()
    start_scheduler()
    serve(app, host="0.0.0.0", port=PORT, threads=8)
