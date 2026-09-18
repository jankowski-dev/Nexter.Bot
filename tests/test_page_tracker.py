"""Проверка page_tracker: извлечение ID и логика уведомлений."""
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


def test_extract_id_select():
    props = {"ID": {"type": "select", "select": {"name": "X-1"}}}
    assert page_tracker._extract_id(props, "ID") == "X-1"


def test_extract_id_missing():
    assert page_tracker._extract_id({}, "ID") == ""


def test_extract_id_formula_string():
    props = {"ID": {"type": "formula", "formula": {"type": "string", "string": "X-1"}}}
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


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _page(pid, id_value):
    return {"id": pid, "properties": {"ID": {"type": "number", "number": id_value}}}


def _fake_send(sent, text):
    sent.append(text)
    return True


def _patch(sent, pages):
    original_post = page_tracker.requests.post
    original_send = page_tracker.notify.send_viber_message
    original_save = page_tracker._save_state
    page_tracker.requests.post = lambda *a, **k: _FakeResponse(
        {"results": pages, "has_more": False}
    )
    page_tracker.notify.send_viber_message = lambda text: _fake_send(sent, text)
    page_tracker._save_state = lambda: None
    return original_post, original_send, original_save


def _restore(originals):
    original_post, original_send, original_save = originals
    page_tracker.requests.post = original_post
    page_tracker.notify.send_viber_message = original_send
    page_tracker._save_state = original_save


def test_poll_first_run_warms_without_sending():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1)])
    try:
        page_tracker._state.clear()
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == []
        assert page_tracker._state["claims"] == {"p1"}
    finally:
        _restore(originals)


def test_poll_second_run_sends_only_new():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1), _page("p2", 2)])
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = {"p1"}
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == ["Получена новая заявка 2"]
        assert page_tracker._state["claims"] == {"p1", "p2"}
    finally:
        _restore(originals)


def test_poll_reset_state_sends_all():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1)])
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = {"p1"}
        page_tracker.reset_state("claims")
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == ["Получена новая заявка 1"]
    finally:
        _restore(originals)


def test_poll_send_failure_not_marked():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1)])
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = set()
        page_tracker.notify.send_viber_message = lambda text: False
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert page_tracker._state["claims"] == set()
    finally:
        _restore(originals)


def test_poll_send_failure_then_success_retries():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1)])
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = set()
        page_tracker.notify.send_viber_message = lambda text: False
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert page_tracker._state["claims"] == set()

        page_tracker.notify.send_viber_message = lambda text: _fake_send(sent, text)
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == ["Получена новая заявка 1"]
        assert page_tracker._state["claims"] == {"p1"}
    finally:
        _restore(originals)


def test_num_to_str_normalizes_integral_float():
    assert page_tracker._num_to_str(123.0) == "123"
    assert page_tracker._num_to_str(1.5) == "1.5"
    assert page_tracker._num_to_str(7) == "7"


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
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_claims_tracker_uses_claims_config():
    import claims_tracker

    captured = {}
    original = page_tracker.poll_new_pages
    page_tracker.poll_new_pages = lambda **kw: captured.update(kw)
    try:
        os.environ["CLAIMS_DB_ID"] = "cdb"
        claims_tracker.check_new_claims()
        assert captured["db_id"] == "cdb"
        assert captured["label"] == "Получена новая заявка"
        assert captured["state_key"] == "claims"
        assert captured["id_field"] == "ID"
        assert captured["filter"] == {"property": "Статус", "select": {"equals": "Новая"}}
    finally:
        page_tracker.poll_new_pages = original


def test_reviews_tracker_uses_reviews_config():
    import reviews_tracker

    captured = {}
    original = page_tracker.poll_new_pages
    page_tracker.poll_new_pages = lambda **kw: captured.update(kw)
    try:
        os.environ["REVIEWS_DB_ID"] = "rdb"
        reviews_tracker.check_new_reviews()
        assert captured["db_id"] == "rdb"
        assert captured["label"] == "Получен новый отзыв"
        assert captured["state_key"] == "reviews"
        assert captured["id_field"] == "ID"
        assert captured.get("filter") is None
    finally:
        page_tracker.poll_new_pages = original


if __name__ == "__main__":
    os.environ.setdefault("NOTION_API_KEY", "test")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
