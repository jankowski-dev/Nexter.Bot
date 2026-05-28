"""
scheduler.py — APScheduler: напоминания распорядка + перерегистрация вебхука.
Расписание обновляется из Notion каждые 10 минут.
"""

import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import requests
import notify
import keyboards as kb
from health_notion import get_schedule

scheduler = BackgroundScheduler()


def _send_reminder(name: str) -> None:
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 🔔 {name}")
    notify.send_viber_keyboard(name, kb.root_keyboard())


def _refresh_webhook() -> None:
    """Периодически перерегистрирует вебхук, чтобы Viber не терял его."""
    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    viber_token = os.environ.get("VIBER_TOKEN", "").strip()
    if not webhook_url or not viber_token:
        return
    try:
        r = requests.post(
            "https://chatapi.viber.com/pa/set_webhook",
            headers={"X-Viber-Auth-Token": viber_token},
            json={"url": webhook_url, "event_types": ["message", "conversation_started", "delivered", "seen", "failed", "subscribed", "unsubscribed"]},
            timeout=15,
        )
        print(f"[SCHED] Webhook refresh: HTTP {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[SCHED] ⚠️ Webhook refresh failed: {e}")


def _refresh_schedule() -> None:
    """Перечитывает расписание из Notion и обновляет cron-задачи."""
    try:
        items = get_schedule()
    except Exception:
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} ⚠️ Ошибка загрузки расписания.")
        return

    for job in scheduler.get_jobs():
        jid = job.id
        if jid.startswith("reminder_"):
            job.remove()

    if not items:
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Расписание пустое.")
        return

    for i, item in enumerate(items):
        try:
            h, m = map(int, item["time"].split(":"))
        except ValueError:
            print(f"[SCHED] ⚠️ Неверное время: '{item['name']}' — {item['time']}")
            continue
        scheduler.add_job(
            lambda name=item["name"]: _send_reminder(name),
            "cron",
            hour=h,
            minute=m,
            id=f"reminder_{i}",
            replace_existing=True,
        )
        print(f"[SCHED] {item['time']} — {item['name']}")


def start_scheduler() -> None:
    scheduler.add_job(
        _refresh_schedule,
        "interval",
        minutes=10,
        id="refresh_schedule",
        max_instances=1,
        coalesce=True,
    )
    print(f"[SCHED] Обновление расписания: каждые 10 мин.")

    scheduler.add_job(
        _refresh_webhook,
        "interval",
        minutes=30,
        id="refresh_webhook",
        max_instances=1,
        coalesce=True,
    )
    print(f"[SCHED] Перерегистрация вебхука: каждые 30 мин.")

    _refresh_schedule()

    scheduler.start()
    print(f"[SCHED] Планировщик запущен.")
