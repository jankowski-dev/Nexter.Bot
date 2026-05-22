"""
app.py — Flask-приложение: вебхук Viber, health-check, тестовые эндпоинты.
"""

import os
import hashlib
import hmac
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
        "silence_mode": signal_tracker.is_silence(),
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
                        handle_message(text)

                elif event_type == "conversation_started":
                    print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} Разговор начат.")
                    handle_conversation_started()

                elif event_type == "webhook":
                    print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} Webhook event.")
                    notify.send_viber_keyboard("Бот активен. Выбери раздел:", kb.root_keyboard())

                else:
                    print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} Событие: {event_type}")

        except Exception as e:
            print(f"[WEBHOOK] {datetime.now().strftime('%H:%M:%S')} ❌ Ошибка: {e}")

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
    messages = signal_tracker.check_signals(deals) if deals else []

    send_to_viber = request.args.get("send", "false").strip().lower() == "true"
    if send_to_viber and messages:
        for msg in messages:
            notify.send_viber_message(msg)

    return jsonify({
        "status": "ok",
        "deals_count": len(deals),
        "deals": deals,
        "messages_count": len(messages),
        "messages": messages,
        "silence_mode": signal_tracker.is_silence(),
        "sent_to_viber": send_to_viber,
    })


@app.route("/test/simulate", methods=["GET"])
def test_simulate():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    coin = request.args.get("coin", "").strip()
    orders_str = request.args.get("orders", "").strip()

    if not coin:
        return jsonify({"error": "bad_request", "message": "Параметр 'coin' обязателен"}), 400
    if not orders_str:
        return jsonify({"error": "bad_request", "message": "Параметр 'orders' обязателен"}), 400

    try:
        orders = float(orders_str.replace(",", "."))
    except ValueError:
        return jsonify({"error": "bad_request", "message": "orders должен быть числом"}), 400

    profit_all = None
    profit_all_str = request.args.get("profit_all", "").strip()
    if profit_all_str:
        try:
            profit_all = float(profit_all_str.replace(",", "."))
        except ValueError:
            return jsonify({"error": "bad_request", "message": "profit_all должен быть числом"}), 400

    fake_deal = {"coin": coin, "orders_usd": orders, "profit_all_usd": profit_all}
    messages = signal_tracker.check_signals([fake_deal])

    send_to_viber = request.args.get("send", "false").strip().lower() == "true"
    if send_to_viber and messages:
        for msg in messages:
            notify.send_viber_message(msg)

    return jsonify({
        "status": "ok",
        "simulated_deal": fake_deal,
        "messages_count": len(messages),
        "messages": messages,
        "tracker_state": signal_tracker.get_status(),
        "sent_to_viber": send_to_viber,
    })


@app.route("/test/reset", methods=["GET"])
def test_reset():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    signal_tracker.reset_all_states()
    return jsonify({
        "status": "ok",
        "message": "Все состояния трекера сброшены.",
        "tracker_state": signal_tracker.get_status(),
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

