"""Проверка notion_api: извлечение значений свойств."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import notion_api


def test_extract_id_number():
    props = {"ID": {"type": "number", "number": 123}}
    assert notion_api.extract_id(props, "ID") == "123"


def test_extract_id_number_integral_float():
    props = {"ID": {"type": "number", "number": 123.0}}
    assert notion_api.extract_id(props, "ID") == "123"


def test_extract_id_rich_text():
    props = {"ID": {"type": "rich_text", "rich_text": [{"plain_text": "A-1"}]}}
    assert notion_api.extract_id(props, "ID") == "A-1"


def test_extract_id_title():
    props = {"ID": {"type": "title", "title": [{"plain_text": "T-9"}]}}
    assert notion_api.extract_id(props, "ID") == "T-9"


def test_extract_id_unique_id():
    props = {"ID": {"type": "unique_id", "unique_id": {"prefix": "REV", "number": 5}}}
    assert notion_api.extract_id(props, "ID") == "REV-5"


def test_extract_id_unique_id_no_prefix():
    props = {"ID": {"type": "unique_id", "unique_id": {"number": 7}}}
    assert notion_api.extract_id(props, "ID") == "7"


def test_extract_id_formula_number():
    props = {"ID": {"type": "formula", "formula": {"type": "number", "number": 7}}}
    assert notion_api.extract_id(props, "ID") == "7"


def test_extract_id_formula_string():
    props = {"ID": {"type": "formula", "formula": {"type": "string", "string": "X-1"}}}
    assert notion_api.extract_id(props, "ID") == "X-1"


def test_extract_id_select():
    props = {"ID": {"type": "select", "select": {"name": "X-1"}}}
    assert notion_api.extract_id(props, "ID") == "X-1"


def test_extract_id_select_empty():
    props = {"ID": {"type": "select", "select": None}}
    assert notion_api.extract_id(props, "ID") == ""


def test_extract_id_unique_id_empty():
    props = {"ID": {"type": "unique_id", "unique_id": {"number": None}}}
    assert notion_api.extract_id(props, "ID") == ""


def test_extract_id_rich_text_empty():
    props = {"ID": {"type": "rich_text", "rich_text": []}}
    assert notion_api.extract_id(props, "ID") == ""


def test_extract_id_title_empty():
    props = {"ID": {"type": "title", "title": []}}
    assert notion_api.extract_id(props, "ID") == ""


def test_extract_id_missing():
    assert notion_api.extract_id({}, "ID") == ""


def test_getters():
    props = {
        "T": {"type": "title", "title": [{"plain_text": "Заголовок"}]},
        "R": {"type": "rich_text", "rich_text": [{"plain_text": "текст"}]},
        "S": {"type": "select", "select": {"name": "Новая"}},
    }
    assert notion_api.get_title(props, "T") == "Заголовок"
    assert notion_api.get_rich_text(props, "R") == "текст"
    assert notion_api.get_select(props, "S") == "Новая"
    assert notion_api.get_title({}, "T") == ""
    assert notion_api.get_select({}, "S") == ""


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
