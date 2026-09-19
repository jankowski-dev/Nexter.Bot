"""
scheduler.py — APScheduler: напоминания распорядка дня.
Расписание обновляется из Notion каждые 60 минут.
"""

from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

import notify
from health_notion import get_schedule
from logutil import ts

local_now = datetime.now()
utc_now = datetime.utcnow()
_tz_offset = round((local_now - utc_now).total_seconds() / 3600)
_local_tz = timezone(timedelta(hours=_tz_offset))

scheduler = BackgroundScheduler(timezone=_local_tz)
print(f"[SCHED] Часовой пояс: UTC{_tz_offset:+d}")


def _send_reminder(name: str) -> None:
    print(f"[SCHED] {ts()} 🔔 {name}")
    notify.send_viber_message(name)


def _refresh_schedule() -> None:
    """Перечитывает расписание из Notion и обновляет cron-задачи."""
    print(f"[SCHED] {ts()} — обновление расписания...")
    try:
        items = get_schedule()
    except Exception:
        print(f"[SCHED] {ts()} ⚠️ Ошибка загрузки расписания.")
        return

    active_ids = set()
    for item in items:
        try:
            h, m = map(int, item["time"].split(":"))
        except ValueError:
            continue
        job_id = f"reminder_{item['name']}_{item['time']}".replace(" ", "_")
        active_ids.add(job_id)
        scheduler.add_job(
            lambda name=item["name"]: _send_reminder(name),
            "cron",
            hour=h,
            minute=m,
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
            max_instances=1,
        )
        print(f"[SCHED] {item['time']} — {item['name']}")

    for job in scheduler.get_jobs():
        if job.id.startswith("reminder_") and job.id not in active_ids:
            job.remove()
            print(f"[SCHED] Удалена: {job.id}")


def start_scheduler() -> None:
    scheduler.add_job(
        _refresh_schedule,
        "interval",
        minutes=60,
        id="refresh_schedule",
        max_instances=1,
        coalesce=True,
    )
    print(f"[SCHED] Обновление расписания: раз в час.")

    scheduler.start()
    print(f"[SCHED] Планировщик запущен.")

    _refresh_schedule()
