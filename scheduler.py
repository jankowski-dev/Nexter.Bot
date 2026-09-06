"""
scheduler.py — APScheduler: напоминания распорядка и автоинкремент привычек.
Расписание обновляется из Notion каждые 60 минут.
"""

from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

import notify
from health_notion import get_schedule, increment_all_habit_counters

local_now = datetime.now()
utc_now = datetime.utcnow()
_tz_offset = round((local_now - utc_now).total_seconds() / 3600)
_local_tz = timezone(timedelta(hours=_tz_offset))

scheduler = BackgroundScheduler(timezone=_local_tz)
print(f"[SCHED] Часовой пояс: UTC{_tz_offset:+d}")


def _send_reminder(name: str) -> None:
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 🔔 {name}")
    notify.send_viber_message(name)


def _daily_habit_increment() -> None:
    """Каждый день в 22:00 +1 ко всем привычкам."""
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 📊 +1 к привычкам...")
    increment_all_habit_counters()
    notify.send_viber_message("📊 Данные по привычкам за сегодня обновлены.")


def _refresh_schedule() -> None:
    """Перечитывает расписание из Notion и обновляет cron-задачи."""
    now = datetime.now()
    print(f"[SCHED] {now.strftime('%H:%M:%S')} — обновление расписания...")
    try:
        items = get_schedule()
    except Exception:
        print(f"[SCHED] {now.strftime('%H:%M:%S')} ⚠️ Ошибка загрузки расписания.")
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

    scheduler.add_job(
        _daily_habit_increment,
        "cron",
        hour=22,
        minute=0,
        id="daily_habit_increment",
        replace_existing=True,
        misfire_grace_time=600,
        coalesce=True,
        max_instances=1,
    )
    print(f"[SCHED] +1 к привычкам: каждый день в 22:00.")

    scheduler.start()
    print(f"[SCHED] Планировщик запущен.")

    _refresh_schedule()
