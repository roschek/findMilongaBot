# Milonga Finder

Telegram-бот для поиска милонг и практик аргентинского танго в любом городе на ближайшие 4 дня.

## Как работает

Двухфазный AI-агент на базе Google Gemini:

1. **Кэш** — если город уже искали, берём сохранённые сайты с расписаниями
2. **Поиск** — Gemini + встроенный Google Search находит сайты с расписаниями для города
3. **Извлечение** — Gemini читает найденные страницы и извлекает события на 4 дня вперёд
4. **Сохранение** — сайты, давшие результат, кладутся в `sites_db.json` для следующего запроса

Инструменты:
- `read_website` — httpx + Jina Reader как fallback для JS-страниц
- `read_ics` — парсинг ICS/iCal с поддержкой повторяющихся событий (Google Calendar embeds в том числе)
- WordPress ICS probing — автоматическая проверка `/events/feed/?ical=1` у сайтов на WordPress

## Стек

- **python-telegram-bot 22.7** — Telegram-бот
- **Google Gemini Flash** — LLM + встроенный Google Search (grounding)
- **icalendar + recurring-ical-events** — парсинг ICS
- **Jina Reader** (r.jina.ai) — рендеринг JS-страниц
- **Render** — хостинг (worker service)

## Структура

```
app/
  agent.py      # AI-агент: поиск → чтение → извлечение
  tools.py      # read_website, read_ics
  models.py     # MilongaEvent, MilongaResponse
  site_db.py    # JSON-база известных сайтов по городам (TTL 30 дней)
bot/
  main.py       # Telegram-бот
  messages.py   # Строки интерфейса (en, ru, he, es)
  limits.py     # Лимит запросов (20/день), хранится в users_db.json
main.py         # REST API (FastAPI) — опционально
```

## Переменные окружения

```env
GEMINI_API_KEY=       # Google AI Studio → Get API Key
TELEGRAM_BOT_TOKEN=   # @BotFather
API_KEY=              # Опционально: защита REST API
```

## Локальный запуск

```bash
cp .env.example .env
# Заполнить переменные в .env

pip install -r requirements.txt

# Только бот:
python -m bot.main

# Только REST API:
uvicorn main:app --reload
```

## Функции бота

- Поиск милонг и практик по городу на сегодня + 3 дня вперёд
- Нормализация города: «Тбилиси», «Tbilisi», «თბილისი» → одна запись в кэше
- Мультиязычный интерфейс: русский, английский, иврит, испанский (по языку Telegram)
- Лимит 20 запросов/день на пользователя
- Telegram Stars донаты (50 / 250 / 500 ⭐ или произвольная сумма)
- Список источников в каждом ответе
- Команда `/status` — показывает остаток запросов на сегодня

## Деплой на Render

```bash
# render.yaml уже настроен как worker service
# Добавить env vars в Render dashboard:
#   GEMINI_API_KEY, TELEGRAM_BOT_TOKEN
```

## Ограничения

- **Facebook** — события в закрытых группах недоступны без API (требует бизнес-верификацию)
- **JS-календари с кликом по дате** — Jina Reader рендерит страницу, но не может кликать; для таких сайтов нужен Playwright
- **Нет дедупликации событий** — если одна милонга есть на нескольких сайтах, может появиться дважды
- **Файловое хранилище** — `sites_db.json` и `users_db.json` хранятся локально; на Render сбрасываются при перезапуске
