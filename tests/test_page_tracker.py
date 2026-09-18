"""Проверка page_tracker: извлечение ID и логика уведомлений."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def test_extract_id_select():
    props = {"ID": {"type": "select", "select": {"name": "X-1"}}}
    assert page_tracker._extract_id(props, "ID") == "X-1"


def test_extract_id_missing():
    assert page_tracker._extract_id({}, "ID") == ""


if __name__ == "__main__":
    os.environ.setdefault("NOTION_API_KEY", "test")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
