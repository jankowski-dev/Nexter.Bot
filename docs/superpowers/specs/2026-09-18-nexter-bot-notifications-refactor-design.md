# Nexter.Bot — Рефакторинг уведомлений (привычки, заявки, отзывы)

**Дата:** 2026-09-18
**Стек:** Python 3.11+, Flask, APScheduler, Notion API, Viber Bot API
**Хостинг:** Railway

## Обзор

Три изменения в уведомлениях Viber-бота:

1. **Привычки** — убрать ежедневное сообщение об изменении счётчика.
2. **Заявки** — вместо полных данных слать короткое сообщение с ID.
3. **Отзывы** — добавить мониторинг БД «Отзывы» по аналогии с заявками.

## Требования

### 1. Привычки
- Автоинкремент счётчиков в 22:00 (`increment_all_habit_counters`) **остаётся без изменений**.
- Уведомление в Viber «📊 Данные по привычкам за сегодня обновлены.» **удаляется**.

### 2. Заявки
- Убрать отправку полных данных (имя, телефон, адрес, услуга и т.д.) и фото.
- Формат сообщения: `Получена новая заявка {ID}`.
- `{ID}` — значение поля Notion «ID».
- Дедупликация — по `page_id` страницы Notion.
- Интервал опроса — 10 минут (без изменений).
- Фильтр запроса — `Статус = Новая` (без изменений).

### 3. Отзывы
- Новый трекер БД «Отзывы», ID базы — переменная окружения `REVIEWS_DB_ID`.
- Фильтр по статусу отсутствует: следим за появлением новых страниц.
- Формат сообщения: `Получен новый отзыв {ID}`.
- `{ID}` — значение поля Notion «ID».
- Дедупликация — по `page_id`.
- Интервал опроса — 60 минут.

### 4. Прогрев состояния (первый запуск)
При первом опросе трекера (в состоянии ещё нет набора для этого трекера) все
текущие `page_id` записываются в состояние **без отправки сообщений**. Это
защищает от рассылки пачкой всех существующих записей после деплоя/перезапуска.
Применяется и к заявкам, и к отзывам.

## Архитектура

### Новый модуль `page_tracker.py`
Универсальный поллер Notion-базы. Публичный интерфейс:

```python
poll_new_pages(
    db_id: str,
    label: str,          # префикс сообщения, напр. "Получена новая заявка"
    id_field: str,       # имя поля с ID, напр. "ID"
    state_key: str,      # "claims" | "reviews"
    log_tag: str,        # "CLAIMS" | "REVIEWS"
    filter: dict | None = None,
) -> None

reset_state(state_key: str) -> None
```

Внутренние функции:
- `_load_state()` / `_save_state()` — чтение/запись `_notified_ids.json`.
- `_extract_id(props: dict, field: str) -> str` — чистая функция извлечения ID.
- `_query_pages(db_id, filter)` — запрос с пагинацией (`has_more` / `next_cursor`).

### `claims_tracker.py` (после рефакторинга)
Тонкая обёртка:

```python
POLL_INTERVAL_MINUTES = 10

def check_new_claims() -> None:
    page_tracker.poll_new_pages(
        db_id=os.environ.get("CLAIMS_DB_ID", ""),
        label="Получена новая заявка",
        id_field="ID",
        state_key="claims",
        log_tag="CLAIMS",
        filter={"property": "Статус", "select": {"equals": "Новая"}},
    )

def reset_state() -> None:
    page_tracker.reset_state("claims")
```

Удаляются: `_format_message`, `_get_files`, `_decode_file_url`, `_get_phone`,
`_get_checkbox`, `_get_date`, `_get_select`, `_get_text`, `_get_title`,
`_get_files` и вызовы `notify.compress_image` / `notify.send_viber_image`.

### `reviews_tracker.py` (новый)
Тонкая обёртка:

```python
POLL_INTERVAL_MINUTES = 60

def check_new_reviews() -> None:
    page_tracker.poll_new_pages(
        db_id=os.environ.get("REVIEWS_DB_ID", ""),
        label="Получен новый отзыв",
        id_field="ID",
        state_key="reviews",
        log_tag="REVIEWS",
    )

def reset_state() -> None:
    page_tracker.reset_state("reviews")
```

### Извлечение ID (`_extract_id`)
Устойчиво к типу поля Notion. Проверяет по порядку:
- `number` → целое число строкой;
- `rich_text` → `plain_text`;
- `title` → `plain_text`;
- `unique_id` → `{prefix}-{number}` (или просто `{number}`);
- `formula` → результат по его типу (`number` / `string`);
- `select` → `name`.

Если значение пустое — фолбэк на первые 8 символов `page_id`.

### Состояние (`_notified_ids.json`)
Формат:
```json
{
  "claims": ["<page_id>", "..."],
  "reviews": ["<page_id>", "..."]
}
```
Обратная совместимость: если в файле лежит JSON-список — он читается как набор
`claims`, набор `reviews` при этом отсутствует (сработает прогрев).

## Поток данных

```
Scheduler (каждые N мин)
  → {claims,reviews}_tracker.check_*
    → page_tracker.poll_new_pages(db_id, ...)
      → Notion query (пагинация, опц. фильтр)
      → для каждого page:
          если state_key впервые → прогрев: добавить page_id, не слать
          иначе если page_id не в state → добавить, сохранить, send_viber_message(label + ID)
```

## Интеграция

### `scheduler.py`
- `_daily_habit_increment`: убрать строку с `notify.send_viber_message(...)`.
- Добавить задачу `check_reviews` при заданном `REVIEWS_DB_ID`:
  интервал `reviews_tracker.POLL_INTERVAL_MINUTES`, `id="check_reviews"`,
  `max_instances=1`, `coalesce=True`.
- Логирование: `[SCHED] Мониторинг отзывов: каждые 60 мин.` либо предупреждение,
  что `REVIEWS_DB_ID` не задан.

### `app.py`
- Новый эндпоинт `GET /test/reviews` (под `_check_test_secret`):
  `reviews_tracker.reset_state()` + `reviews_tracker.check_new_reviews()`.

### `bot.py`
- Опционально: лог о включённом мониторинге отзывов при старте.

## Обработка ошибок
- Нет `db_id` или API-ключа → тихий выход с логом (как сейчас).
- HTTP-ошибка Notion → лог со статусом и телом, выход без падения планировщика.
- Ошибка сохранения состояния → лог, работа продолжается.
- Пустой ID → фолбэк на `page_id`.

## Вне объёма
- Инфраструктура сжатия картинок в `notify.py` (`compress_image`,
  `cleanup_compressed_cache`) и эндпоинт `/compressed` остаются как есть.
- Формат напоминаний расписания и обработка входящих сообщений не меняются.

## Проверка
- `_extract_id` — чистая функция, проверяется скриптом `python tests/test_page_tracker.py`
  (плюс `_load_state`, `_num_to_str`, логика прогрева/дедупликации и конфиги трекеров).
- End-to-end вручную: `GET /test/claims` и `GET /test/reviews` (с `secret`).
  Эти эндпоинты сбрасывают набор уведомлённых, поэтому при каждом вызове
  отправляют сообщения по всем текущим записям — это нужно для проверки формата.
