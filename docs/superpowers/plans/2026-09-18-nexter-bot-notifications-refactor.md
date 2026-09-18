# Nexter.Bot — Рефакторинг уведомлений: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Убрать ежедневное уведомление о привычках, сократить уведомления по заявкам до `Получена новая заявка {ID}` и добавить аналогичный мониторинг отзывов.

**Architecture:** Новый универсальный модуль `page_tracker.py` инкапсулирует опрос Notion-базы, извлечение ID, дедупликацию по `page_id`, хранение состояния и «прогрев» при первом запуске. `claims_tracker.py` и новый `reviews_tracker.py` — тонкие обёртки с параметрами конкретной базы.

**Tech Stack:** Python 3.11+, APScheduler, Flask, requests, Notion API, Viber API.

**Спека:** `docs/superpowers/specs/2026-09-18-nexter-bot-notifications-refactor-design.md`

---

## Структура файлов

- `page_tracker.py` — **создать**. Универсальный поллер Notion-баз: состояние, `_extract_id`, `poll_new_pages`, `reset_state`.
- `tests/test_page_tracker.py` — **создать**. Проверка `_extract_id` и логики уведомлений/прогрева.
- `claims_tracker.py` — **переписать** в тонкую обёртку над `page_tracker`.
- `reviews_tracker.py` — **создать**. Обёртка для БД «Отзывы» (интервал 60 мин).
- `scheduler.py` — **изменить**. Убрать уведомление привычек, добавить задачу отзывов.
- `app.py` — **изменить**. Добавить `/test/reviews`.
- `bot.py` — **изменить**. Лог о статусе мониторинга отзывов.

---

## Task 1: Модуль `page_tracker.py` — извлечение ID

**Files:**
- Create: `page_tracker.py`
- Test: `tests/test_page_tracker.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_page_tracker.py`:

```python
"""Проверка page_tracker: извлечение ID и логика уведомлений."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import page_tracker


def test_extract_id_number():
    props = {"ID": {"type": "number", "number": 123}}
    assert page_tracker._extract_id(props, "ID") == "123"


def test_extract_id_rich_text():
    props = {"ID": {"type": "rich_text", "rich_text": [{"plain_text": "A-1"}]}}
    assert page_tracker._extract_id(props, "ID") == "A-1"


def test_extract_id_title():
    props = {"ID": {"type": "title", "title": [{"plain_text": "T-9"}]}}
    assert page_tracker._extract_id(props, "ID") == "T-9"


def test_extract_id_unique_id():
    props = {"ID": {"type": "unique_id", "unique_id": {"prefix": "REV", "number": 5}}}
    assert page_tracker._extract_id(props, "ID") == "REV-5"


def test_extract_id_unique_id_no_prefix():
    props = {"ID": {"type": "unique_id", "unique_id": {"number": 7}}}
    assert page_tracker._extract_id(props, "ID") == "7"


def test_extract_id_formula_number():
    props = {"ID": {"type": "formula", "formula": {"type": "number", "number": 7}}}
    assert page_tracker._extract_id(props, "ID") == "7"


def test_extract_id_select():
    props = {"ID": {"type": "select", "select": {"name": "X-1"}}}
    assert page_tracker._extract_id(props, "ID") == "X-1"


def test_extract_id_missing():
    assert page_tracker._extract_id({}, "ID") == ""


if __name__ == "__main__":
    os.environ.setdefault("NOTION_API_KEY", "test")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
```

- [ ] **Step 2: Запустить тест — должен упасть**

Run: `python tests/test_page_tracker.py`
Expected: `ModuleNotFoundError: No module named 'page_tracker'`

- [ ] **Step 3: Создать `page_tracker.py` с реализацией `_extract_id`**

Создать `page_tracker.py`:

```python
"""
page_tracker.py — Универсальный мониторинг новых страниц в базах Notion.
Хранит множество уведомлённых page_id по каждому трекеру и шлёт короткое
сообщение "<label> <ID>" при появлении новой страницы.
"""

import os
import json
import requests
from datetime import datetime

import notify

NOTION_API_VERSION = "2022-06-28"

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_notified_ids.json")
_state: dict[str, set[str]] = {}


def _load_state() -> None:
    global _state
    if not os.path.isfile(_STATE_FILE):
        _state = {}
        return
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            _state = {k: set(v) for k, v in raw.items()}
        elif isinstance(raw, list):
            _state = {"claims": set(raw)}
        else:
            _state = {}
        total = sum(len(v) for v in _state.values())
        print(f"[TRACKER] Загружено {total} ID из кэша.")
    except Exception:
        _state = {}


def _save_state() -> None:
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in _state.items()}, f)
    except Exception as e:
        print(f"[TRACKER] ❌ Ошибка сохранения состояния: {e}")


_load_state()


def _notion_headers() -> dict:
    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def _extract_id(props: dict, field: str) -> str:
    prop = props.get(field)
    if not prop:
        return ""
    ptype = prop.get("type", "")

    if ptype == "number":
        val = prop.get("number")
        return str(int(val)) if val is not None else ""
    if ptype in ("rich_text", "title"):
        arr = prop.get(ptype, [])
        return arr[0]["plain_text"] if arr else ""
    if ptype == "unique_id":
        uid = prop.get("unique_id") or {}
        number = uid.get("number")
        if number is None:
            return ""
        prefix = uid.get("prefix")
        return f"{prefix}-{number}" if prefix else str(number)
    if ptype == "formula":
        formula = prop.get("formula") or {}
        ftype = formula.get("type", "")
        val = formula.get(ftype)
        if val is None:
            return ""
        if ftype == "number":
            return str(int(val))
        return str(val)
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    return ""
```

- [ ] **Step 4: Запустить тест — должен пройти**

Run: `python tests/test_page_tracker.py`
Expected: `OK test_extract_id_*` для всех и `Все тесты пройдены.`

- [ ] **Step 5: Коммит**

```bash
git add page_tracker.py tests/test_page_tracker.py
git commit -m "page_tracker: извлечение ID из полей Notion + тесты"
git push origin main
```

---

## Task 2: Модуль `page_tracker.py` — опрос, прогрев и уведомления

**Files:**
- Modify: `page_tracker.py`
- Modify: `tests/test_page_tracker.py`

- [ ] **Step 1: Дописать падающие тесты в `tests/test_page_tracker.py`**

Добавить перед блоком `if __name__ == "__main__":`:

```python
class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _page(pid, id_value):
    return {"id": pid, "properties": {"ID": {"type": "number", "number": id_value}}}


def _patch(sent, pages):
    original_post = page_tracker.requests.post
    original_send = page_tracker.notify.send_viber_message
    original_save = page_tracker._save_state
    page_tracker.requests.post = lambda *a, **k: _FakeResponse(
        {"results": pages, "has_more": False}
    )
    page_tracker.notify.send_viber_message = lambda text: sent.append(text)
    page_tracker._save_state = lambda: None
    return original_post, original_send, original_save


def _restore(originals):
    original_post, original_send, original_save = originals
    page_tracker.requests.post = original_post
    page_tracker.notify.send_viber_message = original_send
    page_tracker._save_state = original_save


def test_poll_first_run_warms_without_sending():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1)])
    try:
        page_tracker._state.clear()
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == []
        assert page_tracker._state["claims"] == {"p1"}
    finally:
        _restore(originals)


def test_poll_second_run_sends_only_new():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1), _page("p2", 2)])
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = {"p1"}
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == ["Получена новая заявка 2"]
        assert page_tracker._state["claims"] == {"p1", "p2"}
    finally:
        _restore(originals)


def test_poll_reset_state_sends_all():
    os.environ["NOTION_API_KEY"] = "test"
    sent = []
    originals = _patch(sent, [_page("p1", 1)])
    try:
        page_tracker._state.clear()
        page_tracker._state["claims"] = {"p1"}
        page_tracker.reset_state("claims")
        page_tracker.poll_new_pages(
            "db", "Получена новая заявка", "ID", "claims", "CLAIMS"
        )
        assert sent == ["Получена новая заявка 1"]
    finally:
        _restore(originals)
```

- [ ] **Step 2: Запустить тесты — должны упасть**

Run: `python tests/test_page_tracker.py`
Expected: `AttributeError: module 'page_tracker' has no attribute 'poll_new_pages'`

- [ ] **Step 3: Дописать реализацию в `page_tracker.py`**

Добавить в конец `page_tracker.py`:

```python
def _query_pages(db_id: str, filter: dict | None) -> list[dict]:
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = _notion_headers()
    pages: list[dict] = []
    payload: dict = {"page_size": 100}
    if filter:
        payload["filter"] = filter

    while True:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return pages


def poll_new_pages(
    db_id: str,
    label: str,
    id_field: str,
    state_key: str,
    log_tag: str,
    filter: dict | None = None,
) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    if not db_id:
        return

    api_key = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    if not api_key:
        print(f"[{log_tag}] {now} ❌ NOTION_API_KEY не задан.")
        return

    try:
        pages = _query_pages(db_id, filter)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        body = e.response.text[:300] if e.response is not None else ""
        print(f"[{log_tag}] {now} ❌ HTTP {status}: {body}")
        return
    except Exception as e:
        print(f"[{log_tag}] {now} ❌ Ошибка запроса: {e}")
        return

    if state_key not in _state:
        known = set()
        for page in pages:
            page_id = page.get("id", "")
            if page_id:
                known.add(page_id)
        _state[state_key] = known
        _save_state()
        print(f"[{log_tag}] {now} 🌱 Первый запуск: прогрето {len(known)} ID без отправки.")
        return

    known = _state[state_key]
    new_count = 0
    for page in pages:
        page_id = page.get("id", "")
        if not page_id or page_id in known:
            continue
        known.add(page_id)
        _save_state()
        new_count += 1
        props = page.get("properties", {})
        id_value = _extract_id(props, id_field) or page_id[:8]
        notify.send_viber_message(f"{label} {id_value}")
        print(f"[{log_tag}] {now} ✅ Уведомление: {label} {id_value}")

    if new_count == 0:
        print(f"[{log_tag}] {now} — новых нет.")


def reset_state(state_key: str) -> None:
    """Сбрасывает набор уведомлённых для трекера (для тестов)."""
    _state[state_key] = set()
    _save_state()
```

- [ ] **Step 4: Запустить тесты — должны пройти**

Run: `python tests/test_page_tracker.py`
Expected: все `OK test_*` и `Все тесты пройдены.`

- [ ] **Step 5: Коммит**

```bash
git add page_tracker.py tests/test_page_tracker.py
git commit -m "page_tracker: опрос БД, прогрев и дедупликация уведомлений"
git push origin main
```

---

## Task 3: Переписать `claims_tracker.py` как обёртку

**Files:**
- Modify: `claims_tracker.py` (полная замена содержимого)

- [ ] **Step 1: Заменить содержимое `claims_tracker.py`**

Полностью заменить файл на:

```python
"""
claims_tracker.py — Мониторинг новых заявок в Notion.
Каждые N минут опрашивает БД и шлёт короткое уведомление "Получена новая заявка <ID>".
"""

import os

import page_tracker

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

- [ ] **Step 2: Проверить компиляцию и импорт**

Run: `python -m py_compile claims_tracker.py`
Expected: без вывода (успех).

Run: `python -c "import claims_tracker"`
Expected: без ошибок.

- [ ] **Step 3: Коммит**

```bash
git add claims_tracker.py
git commit -m "claims_tracker: короткое уведомление через page_tracker"
git push origin main
```

---

## Task 4: Создать `reviews_tracker.py`

**Files:**
- Create: `reviews_tracker.py`

- [ ] **Step 1: Создать `reviews_tracker.py`**

```python
"""
reviews_tracker.py — Мониторинг новых отзывов в Notion.
Раз в час опрашивает БД и шлёт короткое уведомление "Получен новый отзыв <ID>".
"""

import os

import page_tracker

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

- [ ] **Step 2: Проверить компиляцию и импорт**

Run: `python -m py_compile reviews_tracker.py`
Expected: без вывода (успех).

Run: `python -c "import reviews_tracker"`
Expected: без ошибок.

- [ ] **Step 3: Коммит**

```bash
git add reviews_tracker.py
git commit -m "reviews_tracker: мониторинг новых отзывов (раз в час)"
git push origin main
```

---

## Task 5: Планировщик — убрать уведомление привычек, добавить отзывы

**Files:**
- Modify: `scheduler.py`

- [ ] **Step 1: Убрать уведомление о привычках**

В `scheduler.py` в функции `_daily_habit_increment` удалить строку:

```python
    notify.send_viber_message("📊 Данные по привычкам за сегодня обновлены.")
```

Функция должна принять вид:

```python
def _daily_habit_increment() -> None:
    """Каждый день в 22:00 +1 ко всем привычкам."""
    print(f"[SCHED] {datetime.now().strftime('%H:%M:%S')} 📊 +1 к привычкам...")
    increment_all_habit_counters()
```

- [ ] **Step 2: Импортировать `reviews_tracker`**

В блоке импортов добавить строку после `import claims_tracker`:

```python
import reviews_tracker
```

- [ ] **Step 3: Добавить задачу отзывов в `start_scheduler`**

После блока `if os.environ.get("CLAIMS_DB_ID"): ... else: ...` (перед `scheduler.start()`) добавить:

```python
    if os.environ.get("REVIEWS_DB_ID"):
        scheduler.add_job(
            reviews_tracker.check_new_reviews,
            "interval",
            minutes=reviews_tracker.POLL_INTERVAL_MINUTES,
            id="check_reviews",
            max_instances=1,
            coalesce=True,
        )
        print(f"[SCHED] Мониторинг отзывов: каждые {reviews_tracker.POLL_INTERVAL_MINUTES} мин.")
    else:
        print(f"[SCHED] ⚠️ REVIEWS_DB_ID не задан — мониторинг отзывов отключён.")
```

- [ ] **Step 4: Проверить компиляцию и импорт**

Run: `python -m py_compile scheduler.py`
Expected: без вывода (успех).

Run: `python -c "import scheduler"`
Expected: без ошибок, в логе строка `[SCHED] Часовой пояс: ...`.

- [ ] **Step 5: Коммит**

```bash
git add scheduler.py
git commit -m "scheduler: убрано уведомление привычек, добавлен мониторинг отзывов"
git push origin main
```

---

## Task 6: Эндпоинт `/test/reviews` и лог при старте

**Files:**
- Modify: `app.py`
- Modify: `bot.py`

- [ ] **Step 1: Добавить `/test/reviews` в `app.py`**

В конец `app.py` (после функции `test_claims`) добавить:

```python
@app.route("/test/reviews", methods=["GET"])
def test_reviews():
    if not _check_test_secret():
        return jsonify({"error": "forbidden", "message": "Неверный test secret"}), 403

    import reviews_tracker
    reviews_tracker.reset_state()
    reviews_tracker.check_new_reviews()
    return jsonify({"status": "ok", "message": "Проверка отзывов выполнена."})
```

- [ ] **Step 2: Добавить лог в `bot.py`**

В `bot.py` после блока:

```python
    if os.environ.get("CLAIMS_DB_ID"):
        print(f"[STARTUP] ✅ Мониторинг заявок включён (CLAIMS_DB_ID задан).")
    else:
        print(f"[STARTUP] ⚠️ CLAIMS_DB_ID не задан — мониторинг заявок отключён.")
```

добавить:

```python
    if os.environ.get("REVIEWS_DB_ID"):
        print(f"[STARTUP] ✅ Мониторинг отзывов включён (REVIEWS_DB_ID задан).")
    else:
        print(f"[STARTUP] ⚠️ REVIEWS_DB_ID не задан — мониторинг отзывов отключён.")
```

- [ ] **Step 3: Проверить компиляцию**

Run: `python -m py_compile app.py bot.py`
Expected: без вывода (успех).

- [ ] **Step 4: Коммит**

```bash
git add app.py bot.py
git commit -m "app/bot: эндпоинт /test/reviews и лог мониторинга отзывов"
git push origin main
```

---

## Task 7: Финальная проверка

**Files:**
- Verify only.

- [ ] **Step 1: Прогнать тесты**

Run: `python tests/test_page_tracker.py`
Expected: все `OK test_*` и `Все тесты пройдены.`

- [ ] **Step 2: Проверить компиляцию всех изменённых файлов**

Run: `python -m py_compile page_tracker.py claims_tracker.py reviews_tracker.py scheduler.py app.py bot.py`
Expected: без вывода (успех).

- [ ] **Step 3: Проверить импорт приложения**

Run: `python -c "import app, claims_tracker, reviews_tracker"`
Expected: без ошибок.

- [ ] **Step 4: Ручная end-to-end проверка на Railway (после деплоя)**

1. Открыть `GET /test/claims?secret=<TEST_SECRET>` — приходит `Получена новая заявка <ID>`.
2. Открыть `GET /test/reviews?secret=<TEST_SECRET>` — приходит `Получен новый отзыв <ID>`.
3. Убедиться, что после старта бота (без вызова test-эндпоинтов) массовой рассылки старых записей нет.
4. Убедиться, что в 22:00 приходит только лог `+1 к привычкам...` и **нет** сообщения «Данные по привычкам обновлены».

- [ ] **Step 5: Коммит (если были правки)**

Если по итогам проверок правок не было — пропустить. Иначе:

```bash
git add -A
git commit -m "Правки по итогам финальной проверки"
git push origin main
```
