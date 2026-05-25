# Milonga Finder

Telegram bot that finds Argentine tango milongas and practicas in any city for today and the next 3 days.

## Setup

```bash
cp .env.example .env   # add GEMINI_API_KEY and TELEGRAM_BOT_TOKEN
pip install -r requirements.txt
python -m bot.main
```

## Environment variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) → Get API Key |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `API_KEY` | Optional — protects the REST API |
