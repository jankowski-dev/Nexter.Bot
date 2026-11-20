# Nexter.Bot — Viber task reminders

Python-сервис, который работает только с Nexter System: опрашивает Nexter API, присылает напоминания о задачах и принимает аудио для заметок. Notion не используется.

Архитектура: [`docs/architecture.md`](docs/architecture.md).

## Переменные

| Переменная | Назначение |
| --- | --- |
| `VIBER_TOKEN` | токен Viber-бота |
| `VIBER_USER_ID` | получатель уведомлений |
| `NEXTER_API_URL` | базовый URL API, по умолчанию production |
| `NEXTER_BOT_TOKEN` | bearer-токен для `GET /api/v1/bot/tasks/upcoming` |
| `REMINDER_LEAD_MINUTES` | окно напоминания, по умолчанию 5 |
| `REMINDER_POLL_SECONDS` | интервал опроса, по умолчанию 30 |
| `TEST_SECRET` | секрет для `/test/*` |
| `BOT_TIMEZONE` | часовой пояс, по умолчанию `Europe/Minsk` |
| `MAX_AUDIO_MB` | локальный предел аудио, по умолчанию 8; допустимо 1–20. Должен быть не меньше лимита в `Настройки → ИИ → Аудио`. |
| `WEBHOOK_URL` | публичный URL сервиса для входящих сообщений Viber |

## Проверка

```bash
curl "https://<bot-host>/test/status?secret=<TEST_SECRET>"
curl "https://<bot-host>/test/notify?secret=<TEST_SECRET>"
curl "https://<bot-host>/test/poll?secret=<TEST_SECRET>&minutes=10"
```

`/test/poll` делает один проход опроса и возвращает задачи, по которым отправлено напоминание. Уже отправленные задачи не дублируются в пределах процесса.

## Запуск

```bash
pip install -r requirements.txt
python -u bot.py
```
