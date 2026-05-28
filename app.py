"""
app.py — Flask-приложение: вебхук Viber, health-check, тестовые эндпоинты.
"""

import os
from datetime import datetime

from flask import Flask, request, jsonify

import notify
import notion_reader
import signal_tracker
import keyboards as kb
from dispatcher import handle_conversation_started, handle_message, set_nav, Nav

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "8080"))
TEST_SECRET = os.environ.get("TEST_SECRET", "")
VIBER_TOKEN = os.environ.get("VIBER_TOKEN", "")


def _verify_signature(signature: str, body: str) -> bool:
    return True


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "service": "Nexter.Health — Crypto + Habits Tracker",
    })


@app.route("/webhook", methods=["GET", "POST", "HEAD"])
def webhook():
    if request.method == "HEAD":
        return "", 200

    if request.method == "GET":
        return jsonify({"status": "ok"})

    if request.method == "POST":
        signature = request.headers.get("X-Viber-Content-Signature", "")
        body = request.get_data(as_text=True)

        if not _verify_signature(signature, body):
            print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} ❌ Неверная подпись.")
            return jsonify({"status": "error"}), 403

        try:
            data = request.get_json(silent=True)
            if data:
                event_type = data.get("event", "unknown")

                if event_type == "message":
                    msg = data.get("message", {})
                    text = msg.get("text", "").strip()
                    if text:
                        try:
                            handle_message(text)
                        except Exception as e:
                            print(f"[WEBHOOK] Ошибка в handle_message: {e}")
                            notify.send_viber_keyboard("⚠️ Ошибка. Попробуй ещё раз.", kb.root_keyboard())

                elif event_type == "conversation_started":
                    print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} Разговор начат.")
                    handle_conversation_started()

                elif event_type == "webhook":
                    print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} Webhook event.")

                else:
                    print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} Событие: {event_type}")

        except Exception as e:
            print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка: {e}")
            try:
                notify.send_viber_keyboard("⚠️ Сбой. Попробуй ещё раз.", kb.root_keyboard())
            except Exception:
                pass

        return jsonify({"status": 0})


def _check_test_secret() -> bool:
    if not TEST_SECRET:
        return True
    secret = request.args.get("secret", "")
    return secret == TEST_SECRET


@app.route("/test/check", methods=["GET"])
def test_check():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    deals = notion_reader.read_deals()
    signal_tracker.last_deals = deals

    return jsonify({
        "status": "ok",
        "deals_count": len(deals),
        "deals": deals,
        "report": signal_tracker.get_unified_report(deals),
    })


@app.route("/test/reset", methods=["GET"])
def test_reset():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    signal_tracker.reset_all_states()
    return jsonify({
        "status": "ok",
        "message": "Все состояния трекера сброшены.",
    })


@app.route("/test/schedule", methods=["GET"])
def test_schedule():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    import yaml
    import requests as req

    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "health_config.yaml"), "r", encoding="utf-8") as f:
        hc = yaml.safe_load(f)

    db_id = hc.get("notion", {}).get("schedule_db_id", "")
    name_field = hc.get("schedule_fields", {}).get("name", "Название")
    time_field = hc.get("schedule_fields", {}).get("time", "Время")

    if not db_id:
        return jsonify({"status": "error", "message": "schedule_db_id не задан в health_config.yaml"})

    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    try:
        resp = req.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=headers,
            json={"page_size": 100},
            timeout=15,
        )
        raw_body = resp.text
        if resp.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"Notion вернул {resp.status_code}",
                "body": raw_body,
            })

        data = resp.json()
        results = data.get("results", [])
        sample = results[0].get("properties", {}) if results else {}
        field_names = list(sample.keys()) if sample else []

        items = []
        for page in results:
            props = page.get("properties", {})

            name = ""
            name_prop = props.get(name_field, {})
            if name_prop.get("type") == "title":
                name = (name_prop.get("title") or [{}])[0].get("plain_text", "")
            elif name_prop.get("type") == "rich_text":
                name = (name_prop.get("rich_text") or [{}])[0].get("plain_text", "")

            time_val = ""
            time_prop = props.get(time_field, {})
            if time_prop.get("type") == "rich_text":
                time_val = (time_prop.get("rich_text") or [{}])[0].get("plain_text", "")
            elif time_prop.get("type") == "title":
                time_val = (time_prop.get("title") or [{}])[0].get("plain_text", "")

            if name:
                items.append({"name": name, "time": time_val or "?"})

        count = int(request.args.get("count", "1"))
        for item in items[:count]:
            notify.send_viber_message(item["name"])

        return jsonify({
            "status": "ok",
            "total": len(results),
            "parsed": len(items),
            "sent": len(items[:count]),
            "db_fields": field_names,
            "used_name_field": name_field,
            "used_time_field": time_field,
            "items": items,
            "sample_props": {k: v.get("type") for k, v in sample.items()} if sample else {},
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
