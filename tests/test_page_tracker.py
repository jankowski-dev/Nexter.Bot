"""Проверка page_tracker: извлечение ID и состояние уведомлённых страниц."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="backslashreplace")
except Exception:
    pass

import page_tracker


def test_extract_id_number():
    props = {"ID": {"type": "number", "number": 123}}
    assert page_tracker._extract_id(props, "ID") == "123"


def test_extract_id_rich_text():
    props = {"ID": {"type": "rich_text", "rich_text": [{"plain_text": "A-1"}]}}
    assert page_tracker._extract_id(props, "ID") == "A-1"


def test_extract_id_title():
    props = {"ID": {"type": "title", "title": [{"plain_text": "T-9"}]}}
    assert page_tracker._extract_id(props, "ID") == "T-9"


def test_extract_id_unique_id():
    props = {"ID": {"type": "unique_id", "unique_id": {"prefix": "REV", "number": 5}}}
    assert page_tracker._extract_id(props, "ID") == "REV-5"


def test_extract_id_unique_id_no_prefix():
    props = {"ID": {"type": "unique_id", "unique_id": {"number": 7}}}
    assert page_tracker._extract_id(props, "ID") == "7"


def test_extract_id_formula_number():
    props = {"ID": {"type": "formula", "formula": {"type": "number", "number": 7}}}
    assert page_tracker._extract_id(props, "ID") == "7"


def test_extract_id_formula_string():
    props = {"ID": {"type": "formula", "formula": {"type": "string", "string": "X-1"}}}
    assert page_tracker._extract_id(props, "ID") == "X-1"


def test_extract_id_select():
    props = {"ID": {"type": "select", "select": {"name": "X-1"}}}
    assert page_tracker._extract_id(props, "ID") == "X-1"


def test_extract_id_select_empty():
    props = {"ID": {"type": "select", "select": None}}
    assert page_tracker._extract_id(props, "ID") == ""


def test_extract_id_unique_id_empty():
    props = {"ID": {"type": "unique_id", "unique_id": {"number": None}}}
    assert page_tracker._extract_id(props, "ID") == ""


def test_extract_id_rich_text_empty():
    props = {"ID": {"type": "rich_text", "rich_text": []}}
    assert page_tracker._extract_id(props, "ID") == ""


def test_extract_id_title_empty():
    props = {"ID": {"type": "title", "title": []}}
    assert page_tracker._extract_id(props, "ID") == ""


def test_extract_id_missing():
    assert page_tracker._extract_id({}, "ID") == ""


def test_num_to_str_normalizes_integral_float():
    assert page_tracker._num_to_str(123.0) == "123"
    assert page_tracker._num_to_str(1.5) == "1.5"
    assert page_tracker._num_to_str(7) == "7"


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
