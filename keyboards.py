"""
keyboards.py — Все Viber-клавиатуры для бота.
"""


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
    return {
        "Type": "keyboard",
        "DefaultHeight": False,
        "ButtonsGroupColumns": 6,
        "ButtonsGroupRows": 2,
        "Buttons": [
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Текущий отчет",
                "Text": "📊 Тек. отчет", "TextSize": "regular",
                "BgColor": "#F6F6F6", "TextHAlign": "center",
            },
            {
                "Columns": 3, "Rows": 1,
                "ActionType": "reply", "ActionBody": "Статистика",
                "Text": "📈 Статистика", "TextSize": "regular",
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
