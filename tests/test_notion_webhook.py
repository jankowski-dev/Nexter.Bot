"""Проверка notion_webhook: подпись, маршрутизация событий и уведомления."""
import hashlib
import hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")

import notion_webhook
import page_tracker


def test_verify_signature():
    body = b'{"type":"page.created"}'
    secret = "secret_test"
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert notion_webhook.verify_signature(body, sig, secret) is True
    assert notion_webhook.verify_signature(body, "sha256=bad", secret) is False
    assert notion_webhook.verify_signature(body, sig, "") is False
    assert notion_webhook.verify_signature(body, "", secret) is False


def test_normalize_id():
    assert notion_webhook._normalize_id("365C8F4B-4994-80C0-A2DA-D34B5817F704") == "365c8f4b499480c0a2dad34b5817f704"
    assert notion_webhook._normalize_id("") == ""


def test_tracker_for_parent():
    os.environ["CLAIMS_DB_ID"] = "365c8f4b-4994-80c0-a2da-d34b5817f704"
    os.environ["REVIEWS_DB_ID"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    key, cfg = notion_webhook._tracker_for_parent("365c8f4b499480c0a2dad34b5817f704")
    assert key == "claims"
    assert cfg["label"] == "Получена новая заявка"
    key2, _ = notion_webhook._tracker_for_parent("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert key2 == "reviews"
    key3, _ = notion_webhook._tracker_for_parent("11111111-2222-3333-4444-555555555555")
    assert key3 is None
    key4, _ = notion_webhook._tracker_for_parent("")
    assert key4 is None


def test_handle_event_ignores_other_types():
    assert notion_webhook.handle_event({"type": "page.content_updated"}) is True
    assert notion_webhook.handle_event({}) is True


def _patch(sent, marked, page, already=False):
    originals = (
        notion_webhook._fetch_page,
        notion_webhook.notify.send_viber_message,
        page_tracker.ensure_warmed,
        page_tracker.already_notified,
        page_tracker.mark_notified,
    )
    notion_webhook._fetch_page = lambda pid: page
    notion_webhook.notify.send_viber_message = lambda text: (sent.append(text), True)[1]
    page_tracker.ensure_warmed = lambda *a, **k: None
    page_tracker.already_notified = lambda *a, **k: already
    page_tracker.mark_notified = lambda sk, pid: marked.append((sk, pid))
    return originals


def _restore(originals):
    (
        notion_webhook._fetch_page,
        notion_webhook.notify.send_viber_message,
        page_tracker.ensure_warmed,
        page_tracker.already_notified,
        page_tracker.mark_notified,
    ) = originals


def _payload(parent_id):
    return {
        "type": "page.created",
        "entity": {"id": "page1", "type": "page"},
        "data": {"parent": {"id": parent_id, "type": "database"}},
    }


def test_handle_event_notifies_new_review():
    os.environ["REVIEWS_DB_ID"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    sent, marked = [], []
    page = {"properties": {"ID": {"type": "number", "number": 42}}}
    originals = _patch(sent, marked, page)
    try:
        assert notion_webhook.handle_event(_payload("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")) is True
        assert sent == ["Получен новый отзыв 42"]
        assert marked == [("reviews", "page1")]
    finally:
        _restore(originals)


def test_handle_event_skips_duplicate():
    os.environ["REVIEWS_DB_ID"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    sent, marked = [], []
    page = {"properties": {"ID": {"type": "number", "number": 42}}}
    originals = _patch(sent, marked, page, already=True)
    try:
        assert notion_webhook.handle_event(_payload("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")) is True
        assert sent == []
        assert marked == []
    finally:
        _restore(originals)


def test_handle_event_skips_claim_not_new_status():
    os.environ["CLAIMS_DB_ID"] = "365c8f4b-4994-80c0-a2da-d34b5817f704"
    sent, marked = [], []
    page = {
        "properties": {
            "ID": {"type": "number", "number": 5},
            "Статус": {"type": "select", "select": {"name": "Черновик"}},
        }
    }
    originals = _patch(sent, marked, page)
    try:
        assert notion_webhook.handle_event(_payload("365c8f4b499480c0a2dad34b5817f704")) is True
        assert sent == []
        assert marked == []
    finally:
        _restore(originals)


def test_handle_event_notifies_new_claim():
    os.environ["CLAIMS_DB_ID"] = "365c8f4b-4994-80c0-a2da-d34b5817f704"
    sent, marked = [], []
    page = {
        "properties": {
            "ID": {"type": "number", "number": 5},
            "Статус": {"type": "select", "select": {"name": "Новая"}},
        }
    }
    originals = _patch(sent, marked, page)
    try:
        assert notion_webhook.handle_event(_payload("365c8f4b499480c0a2dad34b5817f704")) is True
        assert sent == ["Получена новая заявка 5"]
        assert marked == [("claims", "page1")]
    finally:
        _restore(originals)


if __name__ == "__main__":
    os.environ.setdefault("NOTION_API_KEY", "test")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
