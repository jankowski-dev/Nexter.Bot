"""
app.py — Flask-приложение: health-check, Viber webhook и тестовые эндпоинты.
"""

import hashlib
import hmac
import os
import tempfile
import threading

from flask import Flask, jsonify, request
import requests

import nexter_api
import notify
import scheduler
import transcriber
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


AUDIO_TYPES = {
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
}
MAX_AUDIO_BYTES = 2_400_000


def _audio_mime(filename: str) -> str | None:
    return AUDIO_TYPES.get(os.path.splitext(filename.lower())[1])


def _process_audio(
    message_token: str,
    filename: str,
    mime: str,
    audio_bytes: bytes,
) -> None:
    suffix = os.path.splitext(filename)[1] or ".m4a"
    path = ""
    try:
        notify.send_viber_message("Обрабатываю аудио…")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(audio_bytes)
            path = handle.name

        transcript, duration = transcriber.transcribe(path)
        if not transcript:
            notify.send_viber_message("Не удалось распознать речь в аудио.")
            return

        result = nexter_api.create_audio_note(
            viber_message_id=message_token,
            transcript=transcript,
            audio_bytes=audio_bytes,
            audio_mime=mime,
            audio_name=filename,
            duration_seconds=duration,
        )
        if result.get("status") == "done":
            notify.send_viber_message(f"Заметка создана: {result.get('title') or 'без названия'}")
        else:
            notify.send_viber_message(f"Не удалось создать заметку: {result.get('error') or 'ошибка'}")
    except Exception as error:
        print(f"[AUDIO] {ts()} ❌ {error}")
        notify.send_viber_message(f"Ошибка обработки аудио: {str(error)[:200]}")
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


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
                return jsonify({"status": 0})

            filename = str(message.get("file_name") or "audio.m4a")
            mime = _audio_mime(filename)
            if not mime:
                notify.send_viber_message("Поддерживаются аудиофайлы m4a, mp3, ogg, wav и webm.")
                return jsonify({"status": 0})

            try:
                response = requests.get(
                    media,
                    headers={"X-Viber-Auth-Token": os.environ.get("VIBER_TOKEN", "")},
                    timeout=30,
                )
                if response.status_code != 200:
                    raise RuntimeError(f"Viber media HTTP {response.status_code}")
                if len(response.content) > MAX_AUDIO_BYTES:
                    notify.send_viber_message("Аудио слишком большое. Максимум 2.4 МБ.")
                    return jsonify({"status": 0})

                token = str(data.get("message_token") or message.get("message_token") or "")
                if not token:
                    import hashlib as _hashlib
                    token = _hashlib.sha256(response.content).hexdigest()[:40]

                print(
                    f"[WEBHOOK] {ts()} audio {filename} mime={mime} "
                    f"bytes={len(response.content)} token={token}"
                )
                threading.Thread(
                    target=_process_audio,
                    args=(token, filename, mime, response.content),
                    daemon=True,
                    name="viber-audio",
                ).start()
            except Exception as error:
                print(f"[WEBHOOK] {ts()} file download failed: {error}")
                notify.send_viber_message("Не удалось скачать аудио.")
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
