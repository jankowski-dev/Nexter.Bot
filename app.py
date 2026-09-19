"""
app.py — Flask-приложение: вебхук Viber, вебхук Notion, health-check, тесты.
"""

import hmac
import hashlib
import os

from flask import Flask, request, jsonify

import notify
import notion_webhook
from dispatcher import handle_conversation_started, handle_message
from logutil import ts

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "8080"))
TEST_SECRET = os.environ.get("TEST_SECRET", "")


def _verify_viber_signature(signature: str, body: bytes) -> bool:
    """HMAC-SHA256 от тела запроса с ключом VIBER_TOKEN."""
    token = os.environ.get("VIBER_TOKEN", "")
    if not token or not signature:
        return False
    expected = hmac.new(token.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "service": "Nexter.Bot — Schedule, Claims & Reviews Tracker",
        "webhook_url": os.environ.get("WEBHOOK_URL", "не задан"),
    })


@app.route("/ping", methods=["GET"])
def ping():
    print(f"[APP] {ts()} GET /ping")
    return "pong", 200


@app.route("/webhook", methods=["GET", "POST", "HEAD"])
def webhook():
    if request.method == "HEAD":
        return "", 200

    if request.method == "GET":
        print(f"[APP] {ts()} GET /webhook — ok")
        return jsonify({"status": "ok"})

    if request.method == "POST":
        print(f"[APP] {ts()} POST /webhook")
        raw = request.get_data()
        signature = request.headers.get("X-Viber-Content-Signature", "")

        if not _verify_viber_signature(signature, raw):
            print(f"[WEBHOOK] {ts()} ❌ Неверная подпись.")
            return jsonify({"status": "error"}), 403

        try:
            data = request.get_json(silent=True)
            if data:
                event_type = data.get("event", "unknown")

                if event_type == "message":
                    msg = data.get("message", {})
                    text = msg.get("text", "").strip()
                    print(f"[WEBHOOK] {ts()} 📨 message: '{text}' (len={len(text)})")
                    if text:
                        try:
                            handle_message(text)
                        except Exception as e:
                            print(f"[WEBHOOK] Ошибка в handle_message: {e}")
                            notify.send_viber_message("⚠️ Ошибка. Попробуй ещё раз.")

                elif event_type == "conversation_started":
                    print(f"[WEBHOOK] {ts()} Разговор начат.")
                    handle_conversation_started()

                elif event_type == "webhook":
                    print(f"[WEBHOOK] {ts()} Webhook event.")

                else:
                    print(f"[WEBHOOK] {ts()} Событие: {event_type}")

        except Exception as e:
            print(f"[WEBHOOK] {ts()} ❌ Ошибка: {e}")

        return jsonify({"status": 0})


@app.route("/notion/webhook", methods=["POST"])
def notion_webhook_route():
    raw = request.get_data()
    payload = request.get_json(silent=True) or {}

    if "verification_token" in payload:
        token = payload.get("verification_token", "")
        print(f"[NOTION-WH] 🔑 verification_token = {token}")
        return jsonify({"status": "ok"})

    secret = os.environ.get("NOTION_WEBHOOK_SECRET", "")
    if secret:
        signature = request.headers.get("X-Notion-Signature", "")
        if not notion_webhook.verify_signature(raw, signature, secret):
            print(f"[NOTION-WH] {ts()} ❌ Неверная подпись.")
            return jsonify({"status": "error"}), 403
    else:
        print(f"[NOTION-WH] {ts()} ⚠️ NOTION_WEBHOOK_SECRET не задан — подпись не проверяется.")

    try:
        ok = notion_webhook.handle_event(payload)
    except Exception as e:
        print(f"[NOTION-WH] ❌ Ошибка обработки: {e}")
        return jsonify({"status": "error"}), 500

    if not ok:
        return jsonify({"status": "retry"}), 500
    return jsonify({"status": "ok"})


def _check_test_secret() -> bool:
    if not TEST_SECRET:
        return True
    secret = request.args.get("secret", "")
    return secret == TEST_SECRET


@app.route("/test/schedule", methods=["GET"])
def test_schedule():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    import health_notion
    items = health_notion.get_schedule()
    count = int(request.args.get("count", "1"))
    for item in items[:count]:
        notify.send_viber_message(item["name"])
    return jsonify({
        "status": "ok",
        "total": len(items),
        "sent": len(items[:count]),
        "items": items,
    })
