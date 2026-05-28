"""
crypto.py — Обработчики меню Crypto.
"""

import threading
import notify
import notion_reader
import signal_tracker
import keyboards as kb


def show_report() -> None:
    def _do():
        deals = notion_reader.read_deals()
        report = signal_tracker.get_unified_report(deals)
        notify.send_viber_keyboard(report, kb.crypto_keyboard())
    threading.Thread(target=_do, daemon=True).start()


def show_trade_stats() -> None:
    def _do():
        rows = notion_reader.read_stats()
        if not rows:
            notify.send_viber_keyboard(
                "📈 Торговая статистика\n\nНет данных. Проверь stats в crypto_config.yaml.",
                kb.crypto_keyboard(),
            )
            return

        lines = ["📈 Торговая статистика", ""]
        for row in rows:
            lines.append(row["name"])
            lines.append(row["value"])
            lines.append("")

        notify.send_viber_keyboard("\n".join(lines), kb.crypto_keyboard())
    threading.Thread(target=_do, daemon=True).start()
