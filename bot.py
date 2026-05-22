"""
bot.py — Точка входа.
"""

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
    signal_tracker.set_profit_step(float(crypto_cfg.get("tracking", {}).get("profit_step", 5)))
    check_interval = int(crypto_cfg.get("tracking", {}).get("check_interval_minutes", 3))

    # Load health configs
    health_notion.load_config()
    health.load_config()

    health_cfg = _load_yaml("health_config.yaml")

    print(f"[STARTUP] {datetime.now().strftime('%H:%M:%S')} 🚀 Запуск на порту {PORT}...")
    print(f"[STARTUP] Crypto DB: {crypto_cfg.get('notion', {}).get('database_id', 'не задан')}")
    print(f"[STARTUP] Health DB: {health_cfg.get('notion', {}).get('habits_db_id', 'не задан')}")
    print(f"[STARTUP] Schedule DB: {health_cfg.get('notion', {}).get('schedule_db_id', 'не задан')}")
    print(f"[STARTUP] Интервал проверки сделок: {check_interval} мин.")
    print(f"[STARTUP] Шаг прибыли для уведомлений: ${crypto_cfg.get('tracking', {}).get('profit_step', 5)}")

    if TEST_SECRET:
        print(f"[STARTUP] 🔐 Тестовые эндпоинты защищены.")
    else:
        print(f"[STARTUP] ⚠️ TEST_SECRET не задан — тестовые эндпоинты открыты!")

    # Инициализация состояний трекера
    deals = notion_reader.read_deals()
    if deals:
        signal_tracker.check_signals(deals)
        print(f"[STARTUP] Загружено {len(deals)} монет.")
    else:
        print(f"[STARTUP] Монеты не найдены.")

    # Запуск планировщика
    start_scheduler(check_interval)

    # Регистрация вебхука Viber (чтобы conversation_started работал)
    webhook_url = os.environ.get("WEBHOOK_URL", "")
    if webhook_url:
        try:
            r = requests.post(
                "https://chatapi.viber.com/pa/set_webhook",
                headers={"X-Viber-Auth-Token": os.environ.get("VIBER_TOKEN", "")},
                json={"url": webhook_url, "event_types": ["delivered", "seen", "failed", "conversation_started"]},
                timeout=15,
            )
            print(f"[STARTUP] Webhook: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"[STARTUP] ⚠️ Webhook registration failed: {e}")

    # Сразу шлём клавиатуру при старте
    notify.send_viber_keyboard("Бот запущен. Выбери раздел:", kb.root_keyboard())

    print(f"[STARTUP] 🌐 Waitress WSGI-сервер запущен.")
    serve(app, host="0.0.0.0", port=PORT)
