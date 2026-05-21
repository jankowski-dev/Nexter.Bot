"""
scheduler.py — APScheduler: периодическая проверка сделок + напоминания распорядка.
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import notify
import notion_reader
import signal_tracker
from health_notion import get_schedule

scheduler = BackgroundScheduler()


def _scheduled_crypto_check() -> None:
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Проверка сигналов...")

    if signal_tracker.is_silence():
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 🔇 Тишина — пропущено.")
        return

    deals = notion_reader.read_deals()
    if not deals:
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Нет активных монет.")
        return

    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Загружено {len(deals)} монет.")
    messages = signal_tracker.check_signals(deals)

    if messages:
        for msg in messages:
            notify.send_viber_message(msg)
    else:
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Без изменений.")


def _send_reminder(name: str) -> None:
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Напоминание: {name}")
    notify.send_viber_message(name)


def start_scheduler(check_interval_minutes: int = 3) -> None:
    scheduler.add_job(
        _scheduled_crypto_check,
        "interval",
        minutes=check_interval_minutes,
        id="signal_check",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    print(f"[SCHED] Проверка сделок: каждые {check_interval_minutes} мин.")

    try:
        items = get_schedule()
    except Exception:
        items = []

    for i, item in enumerate(items):
        try:
            h, m = map(int, item["time"].split(":"))
        except ValueError:
            print(f"[SCHED] ⚠️ Неверное время для '{item['name']}': {item['time']}")
            continue
        job_id = f"schedule_{i}"
        scheduler.add_job(
            lambda name=item["name"]: _send_reminder(name),
            "cron",
            hour=h,
            minute=m,
            id=job_id,
            replace_existing=True,
        )
        print(f"[SCHED] Напоминание '{item['name']}' в {item['time']}")

    scheduler.start()
    print(f"[SCHED] Планировщик запущен.")
