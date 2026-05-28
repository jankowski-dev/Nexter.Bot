"""
crypto.py — Обработчики меню Crypto.
"""

import threading
import notify
import notion_reader
import signal_tracker


def show_report() -> None:
    def _do():
        deals = notion_reader.read_deals()
        report = signal_tracker.get_unified_report(deals)
        notify.send_viber_message(report)
    threading.Thread(target=_do, daemon=True).start()


def show_trade_stats() -> None:
    def _do():
        rows = notion_reader.read_stats()
        if not rows:
            notify.send_viber_message(
                "📈 Торговая статистика\n\nНет данных."
            )
            return

        lines = ["📈 Торговая статистика", ""]
        for row in rows:
            lines.append(row["name"])
            lines.append(row["value"])
            lines.append("")

        notify.send_viber_message("\n".join(lines))
    threading.Thread(target=_do, daemon=True).start()
