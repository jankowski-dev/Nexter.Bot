import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nexter_api
import notify
import scheduler


def test_poll_sends_once():
    due = (datetime.now(timezone.utc) + timedelta(minutes=4)).isoformat()
    tasks = [{"id": "task-1", "title": "Проверить отчёт", "dueAt": due, "tags": ["work"]}]
    sent: list[str] = []

    with patch.object(nexter_api, "configured", return_value=True), patch.object(
        nexter_api, "fetch_upcoming", return_value=tasks
    ), patch.object(notify, "send_viber_message", side_effect=lambda text: sent.append(text) or True):
        scheduler.reset_sent()
        first = scheduler.poll_once(5)
        second = scheduler.poll_once(5)

    assert len(first) == 1
    assert second == []
    assert len(sent) == 1
    assert "Проверить отчёт" in sent[0]
    assert "Теги: work" in sent[0]


def test_poll_skips_past_tasks():
    due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    tasks = [{"id": "task-2", "title": "Старая", "dueAt": due, "tags": []}]

    with patch.object(nexter_api, "configured", return_value=True), patch.object(
        nexter_api, "fetch_upcoming", return_value=tasks
    ), patch.object(notify, "send_viber_message", return_value=True):
        scheduler.reset_sent()
        assert scheduler.poll_once(5) == []


def test_poll_reports_api_error():
    with patch.object(nexter_api, "configured", return_value=True), patch.object(
        nexter_api, "fetch_upcoming", side_effect=RuntimeError("boom")
    ):
        assert scheduler.poll_once(5) == []
        assert "boom" in (scheduler.status()["lastError"] or "")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
