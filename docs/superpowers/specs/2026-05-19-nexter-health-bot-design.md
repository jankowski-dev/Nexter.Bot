# Nexter.Health — Viber Bot Design Spec

**Date:** 2026-05-19
**Stack:** Python 3.11+, Flask, APScheduler, Notion API, Viber Bot API
**Hosting:** Railway

## Overview

Personal Viber bot for tracking healthy habits. Three features:
1. **Statistics** — read habit counters from Notion and display them
2. **Daily survey** — bot polls user about each habit, updates Notion counters
3. **Daily schedule** — bot sends reminder messages at configured times

## 1. Project Structure

```
nexter.health/
├── config.yaml
├── main.py                  # Flask + APScheduler
├── bot.py                   # Viber webhook handler, keyboards, survey logic
├── notion.py                # Notion API client
├── survey.py                # In-memory survey state manager
├── requirements.txt
└── Dockerfile
```

## 2. Configuration

### config.yaml
```yaml
habits_fields:
  name: "Название"
  days_without: "Дней без"     # Formula — read only
  counter: "Счетчик"           # Number — updated on answer

schedule_fields:
  name: "Название"
  time: "Время"

habits:
  - "Курение"
  - "Алкоголь"
  - "Кофе"

survey:
  start_time: "09:00"

schedule:
  - name: "Тренировка"
    time: "10:30"
  - name: "Обед"
    time: "13:00"
```

### Railway Variables
| Variable               | Description              |
|------------------------|--------------------------|
| `VIBER_AUTH_TOKEN`     | Viber bot token          |
| `NOTION_API_KEY`       | Notion integration key   |
| `NOTION_HABITS_DB_ID`  | Habits database ID       |
| `NOTION_SCHEDULE_DB_ID`| Schedule database ID     |

## 3. Components

### bot.py — Viber handler
- Validates Viber webhook signatures
- Default keyboard: `[ Статистика ]`
- Statistics: reads Notion habits, sends formatted report
- Survey mode: `[ Да ] [ Нет ]` for each habit

### notion.py — Notion API
- `get_habits_stats()` → `{name: days_without}`
- `update_all_counters({name: new_value})` — single API call
- `get_schedule_items()` → `[{name, time}]`

### survey.py — In-memory state
- `state = {"active": False, "index": 0, "answers": {}}`
- `start()`, `answer(habit, yes/no)`, `current_habit()`, `is_active()`, `get_all_answers()`

## 4. Data Flows

### Statistics
User taps "Статистика" → notion.get_habits_stats() → format report → send

### Survey
Scheduler triggers at start_time → send prompt → survey.start() → keyboard: [Да] [Нет] → User answers each habit (cached in memory) → Last answer: notion.update_all_counters() (single call) → "Опрос пройден!" → restore default keyboard

Counter logic: **Да** = reset to 0, **Нет** = +1

### Schedule
Scheduler triggers at HH:MM → send text with item name

## 5. Keyboard States
- **Default:** `[ Статистика ]`
- **During survey:** current question + `[ Да ] [ Нет ]`

## 6. Error Handling
- Notion errors: log + retry once
- Viber errors: log, don't crash scheduler
- Survey state corruption: reset to default
- Unrecognized messages: ignore

## 7. Notion Database Schemas

### Habits DB
| Field     | Type     | Description           |
|-----------|----------|-----------------------|
| Название  | Title    | Habit name            |
| Счетчик   | Number   | Days clean (updated)  |
| Дней без  | Formula  | Derived days (read)   |

### Schedule DB
| Field    | Type  | Description     |
|----------|-------|-----------------|
| Название | Title | Activity name   |
| Время    | Text  | "HH:MM" format  |
