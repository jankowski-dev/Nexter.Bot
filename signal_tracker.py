"""
signal_tracker.py — Логика отслеживания прибыли ордеров.
Конфигурация min_profit_change из crypto_config.yaml.
"""

from datetime import datetime

silence_mode: bool = False
coin_states: dict[str, dict] = {}
last_deals: list[dict] = []

_min_change: float = 10.0


def set_min_change(value: float) -> None:
    global _min_change
    _min_change = value


def _get_state(coin: str) -> dict:
    if coin not in coin_states:
        coin_states[coin] = {"last_orders_usd": 0.0}
    return coin_states[coin]


def set_silence(enabled: bool) -> str:
    global silence_mode
    silence_mode = enabled
    if enabled:
        print(f"[TRACKER] {datetime.now().strftime('%H:%M:%S')} 🔇 Режим тишины ВКЛЮЧЕН.")
        return "🔇 Режим тишины активирован. Бот не будет отправлять уведомления."
    else:
        print(f"[TRACKER] {datetime.now().strftime('%H:%M:%S')} 🔊 Режим тишины ОТКЛЮЧЕН.")
        return "🔊 Бот активирован. Отслеживание прибыли возобновлено."


def is_silence() -> bool:
    return silence_mode


def reset_all_states() -> None:
    global coin_states, last_deals
    coin_states = {}
    last_deals = []
    print(f"[TRACKER] {datetime.now().strftime('%H:%M:%S')} 🔄 Все состояния сброшены.")


def check_signals(deals: list[dict], skip_notify: bool = False) -> list[str]:
    global last_deals
    last_deals = deals

    if silence_mode:
        return []

    triggered = False

    for deal in deals:
        coin = deal.get("coin", "").strip()
        orders = deal.get("orders_usd")

        if not coin or orders is None:
            continue

        state = _get_state(coin)
        last_orders = state.get("last_orders_usd", 0.0)
        diff = abs(orders - last_orders)

        if orders > 0 and last_orders <= 0:
            triggered = True
        elif diff >= _min_change and orders != 0:
            triggered = True

        state["last_orders_usd"] = orders

    if not triggered or skip_notify:
        return []

    report_lines = []
    for deal in deals:
        coin = deal.get("coin", "").strip()
        orders = deal.get("orders_usd")

        if not coin or orders is None:
            continue
        if orders > 0:
            report_lines.append(f"{coin}: 🟢 {orders:.1f} USD")

    if not report_lines:
        return []

    msg = "🔥 Ордера +\n\n" + "\n".join(report_lines)
    print(f"[TRACKER] {datetime.now().strftime('%H:%M:%S')} 📤 Отчёт по {len(report_lines)} монетам отправлен.")
    return [msg]


def get_unified_report(deals: list[dict] | None = None) -> str:
    d = deals if deals else last_deals
    if not d:
        return "Нет данных об ордерах. Дождитесь первой проверки."

    lines = []
    for deal in d:
        coin = deal.get("coin", "").strip()
        orders = deal.get("orders_usd")
        profit_all = deal.get("profit_all_usd")

        if not coin:
            continue

        if orders is not None and orders > 0:
            orders_emoji = "🟢"
        else:
            orders_emoji = "⚪"
        orders_str = f"{orders:.1f} USD" if orders is not None else "—"

        if profit_all is not None:
            profit_str = f"{profit_all:.1f}"
        else:
            profit_str = "—"

        lines.append(f"{coin}: {orders_emoji} {orders_str} ({profit_str})")

    if not lines:
        return "Нет данных об ордерах."

    return "📊 Отчет\n\n" + "\n".join(lines)


def get_status() -> str:
    if not coin_states:
        return "Нет данных о сделках."

    lines = []
    for coin, state in coin_states.items():
        last = state.get("last_orders_usd", 0.0)
        emoji = "🟢" if last > 0 else "⚪"
        lines.append(f"{coin}: {emoji} {last:.1f} USD")

    status = f"📊 Состояние трекера (порог Δ${_min_change:.0f}):\n" + "\n".join(lines)
    if silence_mode:
        status += "\n\n🔇 Режим тишины ВКЛЮЧЕН"
    return status
