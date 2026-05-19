"""
crypto.py — Обработчики меню Crypto.
"""

import notify
import notion_reader
import signal_tracker
import keyboards as kb


def show_report() -> None:
    deals = notion_reader.read_deals()
    if deals:
        signal_tracker.check_signals(deals, skip_notify=True)
    report = signal_tracker.get_unified_report(deals)
    notify.send_viber_keyboard(report, kb.crypto_keyboard())


def show_trade_stats() -> None:
    notify.send_viber_keyboard(
        "📈 Торговая статистика за всё время\n\nЭтот раздел в разработке.",
        kb.crypto_keyboard(),
    )


def toggle_silence(is_silence: bool) -> None:
    if is_silence:
        msg = "🔇 Режим тишины активирован. Уведомления о сделках приостановлены."
    else:
        msg = "🔊 Отслеживание сделок возобновлено."
    signal_tracker.set_silence(is_silence)
    notify.send_viber_keyboard(msg, kb.crypto_keyboard())
