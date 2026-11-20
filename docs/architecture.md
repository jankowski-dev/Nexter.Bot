# Nexter.Bot — architecture

Status: current, 2026-11-20.

The bot has **no Notion integration**. It only works with Nexter System.

## Incoming Viber messages

- `POST /webhook` verifies `X-Viber-Content-Signature` with `VIBER_TOKEN`.
- Text messages are handled by `dispatcher.py`.
- `file` messages from the owner are downloaded and treated as audio notes:
  - `transcriber.py` (faster-whisper, local) produces the transcript;
  - `nexter_api.create_audio_note` posts transcript + original audio to `POST /api/v1/bot/audio-notes`;
  - the API is idempotent by Viber message token and returns the created note title.

Supported audio: `m4a`, `mp4`, `mp3`, `ogg`, `opus`, `wav`, `webm`. The local limit is `MAX_AUDIO_MB` (1–20, default 8) and must not be lower than the API setting.

## Task reminders

- `scheduler.py` polls `GET /api/v1/bot/tasks/upcoming` every `REMINDER_POLL_SECONDS` (default 30).
- The API returns tasks due within the reminder window; the bot sends `⏰ <task title>` via Viber.
- Sent task ids are deduplicated in process memory.
- Timezone: `BOT_TIMEZONE` (default `Europe/Minsk`).

## Configuration

| Variable | Purpose |
| --- | --- |
| `VIBER_TOKEN` | Viber bot token |
| `VIBER_USER_ID` | owner recipient id |
| `NEXTER_API_URL` | Nexter API base URL |
| `NEXTER_BOT_TOKEN` | bearer token for `/api/v1/bot/*` |
| `REMINDER_LEAD_MINUTES` | reminder window, default 5 |
| `REMINDER_POLL_SECONDS` | polling interval, default 30 |
| `MAX_AUDIO_MB` | local audio limit, 1–20 |
| `BOT_TIMEZONE` | task/reminder timezone |
| `WEBHOOK_URL` | public Viber webhook URL |
| `TEST_SECRET` | secret for `/test/*` |

## Removed

- Notion API client, Notion webhook, claims/reviews trackers and the Notion schedule database.
- Production `NOTION_TOKEN`, `NOTION_WEBHOOK_SECRET`, `CLAIMS_DB_ID` and `REVIEWS_DB_ID` were deleted from the hosting service.
