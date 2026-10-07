"""Проверка частоты обновления расписания (регресс: было раз в час → удалённые задачи успевали сработать)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scheduler


def test_refresh_interval_is_minutes():
    """Обновление должно идти часто, иначе удалённые задачи продолжают срабатывать."""
    assert scheduler.REFRESH_MINUTES <= 5


def test_interval_job_uses_configured_minutes():
    import importlib
    importlib.reload(scheduler)
    sched = scheduler.scheduler
    job = sched.add_job(
        scheduler._refresh_schedule,
        "interval",
        minutes=scheduler.REFRESH_MINUTES,
        id="refresh_schedule_test",
    )
    interval = job.trigger.interval.total_seconds()
    assert interval == scheduler.REFRESH_MINUTES * 60
    job.remove()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
