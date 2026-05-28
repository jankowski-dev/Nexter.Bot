"""
scheduler.py — APScheduler: напоминания распорядка.
Расписание обновляется из Notion каждые 10 минут.
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import notify
import keyboards as kb
from health_notion import get_schedule

scheduler = BackgroundScheduler()


def _send_reminder(name: str) -> None:
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 🔔 {name}")
    notify.send_viber_keyboard(name, kb.root_keyboard())


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

    _refresh_schedule()

    scheduler.start()
    print(f"[SCHED] Планировщик запущен.")
