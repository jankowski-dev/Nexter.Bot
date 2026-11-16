"""
scheduler.py — опрос API Nexter и напоминания в Viber.
"""

import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

import nexter_api
import notify
from bot_timezone import LOCAL_TZ, TZ_NAME
from logutil import ts

POLL_SECONDS = int(os.environ.get("REMINDER_POLL_SECONDS", "30"))
LEAD_MINUTES = int(os.environ.get("REMINDER_LEAD_MINUTES", "5"))

scheduler = BackgroundScheduler(timezone=LOCAL_TZ)
print(f"[SCHED] Часовой пояс: {TZ_NAME}")

_sent: dict[str, datetime] = {}
_last_poll_at: datetime | None = None
_last_error: str | None = None
_last_count = 0


def _prune(now: datetime) -> None:
    cutoff = now - timedelta(minutes=15)
    for task_id, due_at in list(_sent.items()):
        if due_at < cutoff:
            _sent.pop(task_id, None)


def _message(item: dict) -> str:
    """Компактный шаблон: эмодзи будильника и текст задачи."""
    title = str(item.get("title") or "Задача")
    return f"⏰ {title}"


def poll_once(minutes: int | None = None) -> list[dict]:
    """Один проход опроса. Возвращает задачи, по которым отправлено напоминание."""
    global _last_poll_at, _last_error, _last_count

    _last_poll_at = datetime.now(LOCAL_TZ)
    window = minutes or LEAD_MINUTES

    if not nexter_api.configured():
        _last_error = "NEXTER_BOT_TOKEN или NEXTER_API_URL не заданы"
        print(f"[SCHED] {ts()} ⚠️ {_last_error}")
        return []

    try:
        items = nexter_api.fetch_upcoming(window)
        _last_error = None
    except Exception as error:
        _last_error = str(error)
        print(f"[SCHED] {ts()} ⚠️ Ошибка опроса: {error}")
        return []

    _last_count = len(items)
    now = datetime.now(LOCAL_TZ)
    _prune(now)
    reminded: list[dict] = []

    for item in items:
        task_id = str(item.get("id") or "")
        raw_due = item.get("dueAt")
        if not task_id or not raw_due:
            continue
        try:
            due_at = datetime.fromisoformat(str(raw_due).replace("Z", "+00:00"))
        except ValueError:
            print(f"[SCHED] {ts()} ⚠️ Некорректный dueAt у задачи {task_id}")
            continue

        if task_id in _sent:
            continue
        if due_at <= now:
            continue

        text = _message(item)
        print(f"[SCHED] {ts()} 🔔 {text.replace(chr(10), ' | ')}")
        notify.send_viber_message(text)
        _sent[task_id] = due_at
        reminded.append(item)

    return reminded


def status() -> dict:
    return {
        "timezone": TZ_NAME,
        "pollSeconds": POLL_SECONDS,
        "leadMinutes": LEAD_MINUTES,
        "lastPollAt": _last_poll_at.isoformat() if _last_poll_at else None,
        "lastError": _last_error,
        "lastCount": _last_count,
        "sentCount": len(_sent),
    }


def reset_sent() -> None:
    _sent.clear()


def start_scheduler() -> None:
    scheduler.add_job(
        poll_once,
        "interval",
        seconds=POLL_SECONDS,
        id="poll_tasks",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    print(f"[SCHED] Опрос API каждые {POLL_SECONDS} сек., окно {LEAD_MINUTES} мин.")
    poll_once()
