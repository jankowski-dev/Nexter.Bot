"""
bot_timezone.py — часовой пояс бота для планировщика и фильтров.
Задаётся переменной окружения BOT_TIMEZONE (IANA, напр. Europe/Minsk).
По умолчанию Europe/Minsk. Серверный пояс (на Railway это UTC) не используется.
"""

import os
from datetime import timezone, tzinfo
from zoneinfo import ZoneInfo

TZ_NAME = os.environ.get("BOT_TIMEZONE", "").strip() or "Europe/Minsk"

try:
    LOCAL_TZ: tzinfo = ZoneInfo(TZ_NAME)
except Exception:
    print(f"[TZ] ⚠️ Неизвестный часовой пояс '{TZ_NAME}' — используется UTC.")
    LOCAL_TZ = timezone.utc
