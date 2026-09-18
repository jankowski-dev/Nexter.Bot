"""Проверка page_tracker: состояние уведомлённых страниц."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="backslashreplace")
except Exception:
    pass

import page_tracker


def test_already_and_mark_notified():
    original_save = page_tracker._save_state
    page_tracker._save_state = lambda: None
    try:
        page_tracker._state.clear()
        assert page_tracker.already_notified("claims", "p1") is False
        page_tracker.mark_notified("claims", "p1")
        assert page_tracker.already_notified("claims", "p1") is True
        assert page_tracker._state["claims"] == {"p1"}
    finally:
        page_tracker._save_state = original_save
        page_tracker._state.clear()


def test_save_state_cleans_tmp_on_failure():
    import tempfile
    import shutil

    original_file = page_tracker._STATE_FILE
    original_dump = page_tracker.json.dump
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "_notified_ids.json")
    page_tracker._STATE_FILE = state_file

    def boom(*a, **k):
        raise ValueError("boom")

    page_tracker.json.dump = boom
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = {"p1"}
        page_tracker._save_state()
        assert not os.path.isfile(state_file + ".tmp")
    finally:
        page_tracker.json.dump = original_dump
        page_tracker._STATE_FILE = original_file
        page_tracker._state.clear()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_load_state_backward_compat_bare_list():
    import tempfile
    import shutil
    import json as _json

    original_file = page_tracker._STATE_FILE
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "_notified_ids.json")
    page_tracker._STATE_FILE = state_file
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            _json.dump(["a", "b"], f)
        page_tracker._state.clear()
        page_tracker._load_state()
        assert page_tracker._state == {"claims": {"a", "b"}}
    finally:
        page_tracker._STATE_FILE = original_file
        page_tracker._state.clear()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
