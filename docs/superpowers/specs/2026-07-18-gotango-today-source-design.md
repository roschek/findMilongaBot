# gotango.today как первичный источник данных

## Контекст и мотивация

Основная стоимость бота — вызовы Gemini (поиск через Google Search + извлечение событий из неструктурированного текста страниц), это и есть источник трат (~600 шек за 2 месяца), которые эта серия фич пытается компенсировать/сократить. gotango.today — специализированный агрегатор танго-событий с URL вида `https://www.gotango.today/en/{city-slug}`, структурированной официальной базой событий от организаторов. Если использовать его как источник до обращения к Gemini, для покрытых городов можно вообще не тратить Gemini-вызовы на поиск и извлечение.

## Исследование (проверено вручную, июль 2026)

- Сайт — Next.js-приложение с отдельным API-бэкендом. Обычный `httpx`-запрос к `/en/{city}` получает ~100KB HTML, но **без реальных данных о событиях** — они подгружаются клиентским JS после гидратации.
- Существующий в проекте Jina Reader-фолбэк (`https://r.jina.ai/{url}`, `app/tools.py:read_website`) корректно рендерит JS и отдаёт реальные данные — подтверждено вручную на `gotango.today/en/buenos-aires`, совпадает с реальным сайтом.
- **Прямой** (без Jina) запрос к `https://www.gotango.today/en/{slug}` уже даёт корректный HTTP-статус от самого origin-сервера: `200` для покрытого города (`buenos-aires`, `new-york`), `404` для непокрытого (`moscow`, `tel-aviv`, `nonexistent-fake-city-xyz123`). Это значит проверку «покрыт ли город» можно делать дешёвым прямым `httpx`-запросом, **без** похода через Jina — Jina нужен только для реально покрытых городов, чтобы вытащить сам список событий.
- URL поддерживает диапазон дат через query-параметры: `?from=YYYY-MM-DD&to=YYYY-MM-DD`. События в ответе группируются по датам с заголовками вида `18 Saturday/July Today`, `19 Sunday/July` — ровно то, что нужно для сопоставления с датами бота.
- HTML-разметка карточки события (получена через Jina с `X-Return-Format: html`) стабильна и легко парсится BeautifulSoup (уже зависимость проекта):
  - Название: `<h3 class="line-clamp-2 ...">{name}</h3>`
  - Время: первый `<span class="font-mono ...">{"15:00 — 19:00"}</span>` в карточке
  - Статус: `<span data-testid="status-chip-scheduled">...Regular schedule</span>` (варианты статуса определяются по `data-testid` атрибуту)
  - Площадка: `<span class="truncate">{venue}</span>`, идущий сразу после `<svg class="... lucide-map-pin ...">`
  - DJ (опционально): `<span class="truncate">TDJ: {dj}</span>`, идущий сразу после `<svg class="... lucide-music ...">`
  - Тип события: текст внутри `<div class="mt-0.5 flex flex-wrap ...">` — значения вида `Milonga`, `Practica`, вероятно также `Workshop`/`Festival`
  - Ссылка на событие: `href` карточки-обёртки (`<a href="/en/event/{uuid}">`) — прямая ссылка на конкретное событие для пользователя
- Точные CSS-классы и структура DOM могут отличаться в деталях (например, для DJ-поля не гарантирована 100% консистентность) — финальная сверка селекторов делается в момент реализации на живой фикстуре, а не в спеке.

## Ключевые решения

- **Место в пайплайне**: gotango.today пробуется **первым шагом**, до `known_sites`/поиска/извлечения. Если город покрыт (200) — используем его данные напрямую и **не** делаем ни одного вызова Gemini для поиска/извлечения (только уже существующая дешёвая нормализация города через `gemini-2.5-flash-lite` остаётся — она нужна для корректности и валидации, что это вообще реальный город). Если не покрыт (404) — падаем в существующий пайплайн (`known_sites` → поиск → извлечение) без изменений.
- **Негативное кэширование не делаем**: непокрытость города не запоминается в `site_db` — при каждом запросе снова делаем дешёвую прямую проверку. Сайт может добавить город позже, это должно подхватываться само.
- **Confidence всегда `"high"`**: это структурированные данные от организаторов, а не догадки LLM из неструктурированного текста.
- **Фильтрация типов**: показываем только события с типом `Milonga`/`Practica` — соответствует текущему заявленному скоупу бота (workshop/festival отбрасываются).
- **Пустой, но покрытый город** (200, событий на диапазон дат нет) — это финальный, достоверный ответ («сегодня и в ближайшие дни ничего нет»), а не повод падать в Gemini-пайплайн — источник официальный и полный для этого города.

## Архитектура

Новый модуль `app/gotango.py` (по аналогии с `app/tools.py`, `app/site_db.py` — один файл, одна ответственность):

```python
async def fetch_gotango_events(city: str, dates: list[str]) -> list[MilongaEvent] | None:
    """
    Returns None if the city isn't covered by gotango.today (404).
    Returns a list (possibly empty) of MilongaEvent if the city IS covered —
    an empty list means "covered, but genuinely nothing scheduled".
    """
```

Вызывается из `run_milonga_agent` (`app/agent.py`) сразу после `_normalize_city`, до текущей логики `known_sites`/`_search_phase`:

```python
canonical_city, city_found = await _normalize_city(client, city)
# ... existing cache-check code unchanged ...
if not city_found:
    return MilongaResponse(..., city_found=False)

gotango_events = await fetch_gotango_events(canonical_city, dates)
if gotango_events is not None:
    result = MilongaResponse(
        city=canonical_city, date=date, events=gotango_events,
        uncertainties=[], sources_found=[...], sources_checked=[...],
        city_found=True,
    )
    # existing Redis result-cache write, unchanged
    return result

# existing known_sites → search → extract pipeline, unchanged, unreached branch stays as-is
```

Внутри `fetch_gotango_events`:
1. Слагифицировать `city` (нижний регистр, небуквенно-цифровые символы → `-`).
2. Прямой `httpx GET` на `https://www.gotango.today/en/{slug}?from={dates[0]}&to={dates[-1]}` (без Jina). `404` → вернуть `None`.
3. Если `200` — тот же URL, но через Jina Reader с `X-Return-Format: html` (чтобы получить пост-JS DOM для парсинга BeautifulSoup, а не markdown с плоской структурой).
4. Распарсить карточки событий по селекторам выше, отфильтровать по типу (`Milonga`/`Practica`), сопоставить каждое событие с датой по секции-заголовку (`18 Saturday/July` → `dates[0]`, и т.д. по порядку секций).
5. Собрать `MilongaEvent` для каждой карточки: `name`, `time` (строка диапазона как есть), `venue`, `dj` (если есть), `source_url` (ссылка на конкретное событие), `confidence="high"`, `notes` = текст статуса (`"Confirmed"`/`"Regular schedule"`), `date`.
6. Вернуть список (может быть пустым — это валидный «покрыт, но пусто» результат).

`sources_checked`/`sources_found` в итоговом `MilongaResponse` заполняются URL gotango.today, который реально проверялся — чтобы существующий блок «источники» в ответе бота (`_sources_line`) корректно показывал источник.

## Вне скоупа

- Полная переработка `_extract_events`/`_search_phase` — они остаются нетронутыми, используются как есть для городов, не покрытых gotango.today.
- Геокодирование/точный адрес площадки — gotango.today даёт только название площадки, не полный адрес; поле `address` остаётся `None` для этих событий (как и для многих текущих источников).
- Цена билета — не видна в карточке события на уровне списка; поле `price` остаётся `None`.
- Кэширование в `site_db` информации «покрыт/не покрыт» — сознательно не делаем (см. «Ключевые решения»).
- Поддержка других языков gotango.today (`/ru/`, `/es/` и т.д.) — используем только `/en/`, т.к. `_normalize_city` уже даёт канонiчное английское имя.
