# Nexter.Bot — архитектура

**Дата:** 2026-09-19
**Стек:** Python 3.11, Flask, Waitress, APScheduler, Notion API, Viber Bot API
**Хостинг:** Railway (Nixpacks)

## Назначение

Личный Viber-бот:
1. Напоминания по расписанию из базы Notion.
2. Уведомления о новых заявках и отзывах из Notion — **через вебхуки** (polling отсутствует).

## Компоненты

| Файл | Ответственность |
|------|-----------------|
| `bot.py` | Точка входа: проверка env, регистрация Viber-вебхука, запуск планировщика и Waitress |
| `app.py` | Flask: `/webhook` (Viber), `/notion/webhook` (Notion), `/`, `/ping`, `/test/*` |
| `notion_webhook.py` | Приём и обработка событий Notion |
| `notion_api.py` | Общий клиент Notion API (заголовки, запросы, извлечение полей) |
| `page_tracker.py` | Состояние уведомлённых страниц (дедупликация) |
| `notify.py` | Фоновая очередь отправки в Viber |
| `logutil.py` | Хелпер `ts()` для таймстампов в логах |
| `health_notion.py` | Расписание дня |
| `scheduler.py` | APScheduler: напоминания по расписанию |
| `dispatcher.py` | Ответы на входящие сообщения Viber |

## Уведомления о заявках и отзывах (вебхуки Notion)

1. В настройках коннекта Notion создаётся подписка на событие `page.created`
   с URL `https://<домен>/notion/webhook`.
2. При создании подписки Notion шлёт одноразовый `verification_token` на наш
   эндпоинт — он логируется и сохраняется в переменную `NOTION_WEBHOOK_SECRET`.
3. Каждый запрос проверяется по заголовку `X-Notion-Signature`
   (HMAC-SHA256 от raw body, ключ — `verification_token`).
4. Обрабатываются только события `page.created`:
   - `entity.id` — ID страницы (page_id);
   - `data.parent.id` — ID базы.
5. Если база совпадает с `CLAIMS_DB_ID` или `REVIEWS_DB_ID` → `GET /v1/pages/{page_id}`.
6. Для заявок дополнительно проверяется `Статус = Новая`.
7. ID для сообщения берётся из поля «ID» (устойчиво к типам
   number/rich_text/title/unique_id/formula/select); фолбэк — первые 8 символов page_id.
8. Дедупликация по `page_id` через `page_tracker` (защита от повторных доставок).
9. Отправка в Viber:
   - заявки: `[ID] Получена заявка`
   - отзывы: `[ID] Получен отзыв`

Событие `page.created` агрегируемое — доставка обычно в пределах ~1 минуты.

## Расписание

- Раз в час база расписания перечитывается из Notion.
- На каждую запись `HH:MM` создаётся cron-задача, которая шлёт текст напоминания.

## Безопасность

- **Viber:** `app._verify_viber_signature` — HMAC-SHA256 от тела запроса с ключом `VIBER_TOKEN`.
- **Notion:** `notion_webhook.verify_signature` — HMAC-SHA256 с ключом `NOTION_WEBHOOK_SECRET`.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `VIBER_TOKEN` | Токен Viber-бота |
| `VIBER_USER_ID` | Получатель уведомлений |
| `WEBHOOK_URL` | Публичный URL Viber-вебхука |
| `NOTION_API_KEY` (или `NOTION_TOKEN`) | Доступ к Notion API |
| `CLAIMS_DB_ID` | База заявок |
| `REVIEWS_DB_ID` | База отзывов |
| `NOTION_WEBHOOK_SECRET` | Токен проверки подписи Notion |
| `TEST_SECRET` | Защита `/test/*` |
| `PORT` | Порт (по умолчанию 8080) |

## Тесты

Запускаются как скрипты (без pytest):
- `tests/test_notion_api.py` — извлечение полей.
- `tests/test_page_tracker.py` — состояние и дедупликация.
- `tests/test_notion_webhook.py` — подпись, маршрутизация, уведомления.
- `tests/test_viber_signature.py` — проверка подписи Viber.

Команда: `python tests/<файл>.py`.

## Вне объёма

- Прунинг `_notified_ids.json` (рост ~1 запись на событие, обрезка рискует
  повторными уведомлениями).
