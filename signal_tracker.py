"""
signal_tracker.py — Хранит последние данные сделок и формирует отчёты.
"""

last_deals: list[dict] = []


def reset_all_states() -> None:
    global last_deals
    last_deals = []


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

    return "📊 Текущий отчёт\n\n" + "\n".join(lines)


def get_status() -> str:
    if not last_deals:
        return "Нет данных о сделках."

    lines = []
    for deal in last_deals:
        coin = deal.get("coin", "N/A")
        orders = deal.get("orders_usd")
        orders_str = f"{orders:.1f}" if orders is not None else "—"
        lines.append(f"{coin}: {orders_str} USD")

    return "📊 Сделки:\n" + "\n".join(lines)
