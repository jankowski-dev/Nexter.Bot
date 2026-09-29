"""Проверка bot_timezone: часовой пояс планировщика не зависит от серверного (Railway = UTC)."""
import importlib
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_tz(name: str | None):
    if name is None:
        os.environ.pop("BOT_TIMEZONE", None)
    else:
        os.environ["BOT_TIMEZONE"] = name
    import bot_timezone
    importlib.reload(bot_timezone)
    return bot_timezone


def test_default_tz_is_minsk():
    mod = _load_tz(None)
    assert mod.TZ_NAME == "Europe/Minsk"
    assert datetime.now(mod.LOCAL_TZ).utcoffset() == timedelta(hours=3)


def test_env_tz_overrides_default():
    mod = _load_tz("Europe/Kaliningrad")
    assert mod.TZ_NAME == "Europe/Kaliningrad"
    assert datetime.now(mod.LOCAL_TZ).utcoffset() == timedelta(hours=2)


def test_invalid_tz_falls_back_to_utc():
    mod = _load_tz("Not/AZone")
    assert mod.LOCAL_TZ is timezone.utc


def test_scheduler_uses_configured_tz_not_server_tz():
    """Сервер в UTC не должен влиять: cron-время считается по поясу бота."""
    _load_tz(None)
    import scheduler
    importlib.reload(scheduler)
    tz = scheduler.scheduler.timezone
    assert datetime.now(tz).utcoffset() == timedelta(hours=3)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
