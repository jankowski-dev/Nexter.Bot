"""
app.py — Flask-приложение: health-check, Viber webhook и тестовые эндпоинты.
"""

import hashlib
import hmac
import os

from flask import Flask, jsonify, request
import requests

import nexter_api
import notify
import scheduler
from logutil import ts

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "8080"))
TEST_SECRET = os.environ.get("TEST_SECRET", "")


def _verify_viber_signature(signature: str, body: bytes) -> bool:
    token = os.environ.get("VIBER_TOKEN", "")
    if not token or not signature:
        return False
    expected = hmac.new(token.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _check_test_secret() -> bool:
    if not TEST_SECRET:
        return False
    return request.args.get("secret", "") == TEST_SECRET


@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "status": "running",
            "service": "Nexter.Bot — Viber task reminders",
            "api": nexter_api.api_url(),
            "apiConfigured": nexter_api.configured(),
            "scheduler": scheduler.status(),
        }
    )


@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


@app.route("/webhook", methods=["GET", "POST", "HEAD"])
def webhook():
    if request.method == "HEAD":
        return "", 200
    if request.method == "GET":
        return jsonify({"status": "ok"})

    raw = request.get_data()
    signature = request.headers.get("X-Viber-Content-Signature", "")
    if not _verify_viber_signature(signature, raw):
        return jsonify({"status": "error"}), 403

    data = request.get_json(silent=True) or {}
    event = data.get("event", "unknown")
    if event == "conversation_started":
        notify.send_viber_message("Nexter.Bot на связи. Напоминания о задачах включены.")
    elif event == "message":
        message = data.get("message") or {}
        sender = (data.get("sender") or {}).get("id", "")
        owner = os.environ.get("VIBER_USER_ID", "")
        media = message.get("media")
        print(
            f"[WEBHOOK] {ts()} message type={message.get('type')!r} "
            f"file={message.get('file_name')!r} size={message.get('file_size')!r} "
            f"duration={message.get('duration')!r} media={bool(media)} "
            f"sender_owner={sender == owner}"
        )

        if message.get("type") == "file" and media:
            if sender != owner:
                notify.send_viber_message("Неизвестный отправитель.")
            else:
                try:
                    response = requests.get(
                        media,
                        headers={"X-Viber-Auth-Token": os.environ.get("VIBER_TOKEN", "")},
                        timeout=30,
                    )
                    print(
                        f"[WEBHOOK] {ts()} file download HTTP {response.status_code} "
                        f"content-type={response.headers.get('content-type')!r} "
                        f"bytes={len(response.content)}"
                    )
                    notify.send_viber_message(
                        f"Файл получен: {message.get('file_name') or 'без имени'}, "
                        f"{len(response.content)} байт"
                    )
                except Exception as error:
                    print(f"[WEBHOOK] {ts()} file download failed: {error}")
                    notify.send_viber_message("Не удалось скачать файл.")
            return jsonify({"status": 0})

        text = str(message.get("text") or "").strip().lower()
        if text in {"тест", "test", "ping"}:
            notify.send_viber_message("Тест Viber: бот на связи ✅")
        else:
            notify.send_viber_message(
                "Я присылаю напоминания о задачах за 5 минут. Напишите «тест» для проверки."
            )
    return jsonify({"status": 0})


@app.route("/test/status", methods=["GET"])
def test_status():
    if not _check_test_secret():
        return jsonify({"error": "forbidden"}), 403
    return jsonify(
        {
            "status": "ok",
            "apiConfigured": nexter_api.configured(),
            "scheduler": scheduler.status(),
        }
    )


@app.route("/test/notify", methods=["GET", "POST"])
def test_notify():
    if not _check_test_secret():
        return jsonify({"error": "forbidden"}), 403
    text = request.args.get("text") or "Тест Viber: бот на связи ✅"
    notify.send_viber_message(text)
    return jsonify({"status": "ok", "text": text})


@app.route("/test/poll", methods=["GET", "POST"])
def test_poll():
    if not _check_test_secret():
        return jsonify({"error": "forbidden"}), 403
    minutes = request.args.get("minutes")
    try:
        window = int(minutes) if minutes else None
    except ValueError:
        return jsonify({"error": "minutes must be an integer"}), 400
    reminded = scheduler.poll_once(window)
    return jsonify(
        {
            "status": "ok",
            "sent": len(reminded),
            "tasks": reminded,
            "scheduler": scheduler.status(),
        }
    )
