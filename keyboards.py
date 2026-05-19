"""
keyboards.py — Все Viber-клавиатуры для бота.
"""

import signal_tracker


def root_keyboard():
    return {
        "Type": "keyboard",
        "DefaultHeight": False,
        "Buttons": [
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Crypto",
                "Text": "💰 Crypto", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Reminder",
                "Text": "🏥 Reminder", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
        ],
    }


def crypto_keyboard():
    silence = signal_tracker.is_silence()
    toggle_text = "🔔 Активация" if silence else "🔇 Тишина"
    toggle_body = "Активация" if silence else "Тишина"
    return {
        "Type": "keyboard",
        "DefaultHeight": False,
        "ButtonsGroupColumns": 6,
        "ButtonsGroupRows": 2,
        "Buttons": [
            {
                "Columns": 2, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Отчет",
                "Text": "📊 Отчет", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 2, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Статистика",
                "Text": "📈 Стат.", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 2, "Rows": 1,
                "ActionType": "reply", "ActionBody": toggle_body,
                "Text": toggle_text, "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 6, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Назад",
                "Text": "← Назад", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
        ],
    }


def reminder_keyboard():
    return {
        "Type": "keyboard",
        "DefaultHeight": False,
        "ButtonsGroupColumns": 6,
        "ButtonsGroupRows": 2,
        "Buttons": [
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Статистика",
                "Text": "📊 Статистика", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Внести данные",
                "Text": "📝 Внести данные", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 6, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Назад",
                "Text": "← Назад", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
        ],
    }


def survey_keyboard():
    return {
        "Type": "keyboard",
        "DefaultHeight": False,
        "Buttons": [
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Да",
                "Text": "✅ Да", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Нет",
                "Text": "❌ Нет", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
        ],
    }
