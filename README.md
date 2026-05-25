# Milonga Finder

Telegram bot that finds Argentine tango milongas and practicas in any city for today and the next 3 days.

## How it works

A two-phase AI agent powered by Google Gemini:

1. **Cache** — if the city was searched before, use the saved schedule sites
2. **Search** — Gemini + built-in Google Search finds tango schedule sites for the city
3. **Extraction** — Gemini reads the pages and extracts events for the next 4 days
4. **Save** — sites that returned results are stored in `sites_db.json` for future requests

Tools used internally:
- `read_website` — httpx fetch + Jina Reader fallback for JS-heavy pages
- `read_ics` — ICS/iCal parsing with recurring event support (Google Calendar embeds included)
- WordPress ICS probing — automatically checks `/events/feed/?ical=1` for WordPress-based sites

## Stack

- **python-telegram-bot 22.7** — Telegram bot
- **Google Gemini Flash** — LLM + built-in Google Search grounding
- **icalendar + recurring-ical-events** — ICS calendar parsing
- **Jina Reader** (r.jina.ai) — free JS page rendering
- **Render** — hosting (worker service)

## Project structure

```
app/
  agent.py      # AI agent: search → fetch → extract
  tools.py      # read_website, read_ics
  models.py     # MilongaEvent, MilongaResponse
  site_db.py    # JSON store of known sites per city (30-day TTL)
bot/
  main.py       # Telegram bot handlers
  messages.py   # UI strings (en, ru, he, es)
  limits.py     # 20 searches/day limit, stored in users_db.json
main.py         # Optional REST API (FastAPI)
```

## Environment variables

```env
GEMINI_API_KEY=       # Google AI Studio → Get API Key
TELEGRAM_BOT_TOKEN=   # @BotFather
API_KEY=              # Optional: protect the REST API
```

## Local setup

```bash
cp .env.example .env
# Fill in the variables

pip install -r requirements.txt

# Bot only:
python -m bot.main

# REST API only:
uvicorn main:app --reload
```

## Bot features

- Search milongas and practicas by city — today + 3 days ahead
- City name normalization: "Тбилиси", "Tbilisi", "თბილისი" → same cache entry
- Multilingual UI: English, Russian, Hebrew, Spanish (follows Telegram language setting)
- 20 searches per user per day
- Telegram Stars donations — 50 / 250 / 500 ⭐ or any custom amount
- Searched sources listed at the bottom of every result
- `/status` command — shows remaining searches for today

## Deploy to Render

`render.yaml` is already configured as a worker service. Add the env vars in the Render dashboard:
`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`.

## Known limitations

- **Facebook** — events posted only in private groups are not accessible without the official API (requires business verification)
- **Click-to-navigate calendars** — Jina Reader renders the page but cannot click dates; a real browser (Playwright) would be needed for those sites
- **No event deduplication** — if a milonga appears on multiple sites it may show up more than once
- **File-based storage** — `sites_db.json` and `users_db.json` are local files; they reset on Render redeploy
