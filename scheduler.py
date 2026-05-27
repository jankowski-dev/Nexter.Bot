"""
scheduler.py — APScheduler: проверка сделок + напоминания распорядка.
Расписание обновляется из Notion каждые 10 минут.
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import notify
import notion_reader
import signal_tracker
import keyboards as kb
from health_notion import get_schedule, set_fasting_counter
import fasting

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
            notify.send_viber_keyboard(msg, kb.root_keyboard())
    else:
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} Без изменений.")


def _send_reminder(name: str) -> None:
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 🔔 {name}")
    notify.send_viber_keyboard(name, kb.root_keyboard())


def _fasting_tick() -> None:
    """Каждый час синхронизирует счётчик голодания с Notion."""
    if not fasting.is_active():
        return
    h = int(fasting.hours())
    set_fasting_counter(h)


def _refresh_schedule() -> None:
    """Перечитывает расписание из Notion и обновляет cron-задачи."""
    try:
        items = get_schedule()
    except Exception:
        print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} ⚠️ Ошибка загрузки расписания.")
        return

    # Сначала удаляем старые задачи расписания
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
        _fasting_tick,
        "interval",
        minutes=60,
        id="fasting_tick",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )
    print(f"[SCHED] Тик голодания: каждый час.")

    _refresh_schedule()

    scheduler.start()
    print(f"[SCHED] Планировщик запущен.")
