# Платный доступ на сутки взамен доната при исчерпании лимита

## Контекст и мотивация

Донат (Telegram Stars, кнопка в главном меню) не окупает расходы на API: за 2 месяца получено ~$10 донатов против ~600 шек (~$165) затрат на запросы. Поиск милонг по городу — ситуативное разовое действие, не ежедневное, поэтому модель "подписка" не подходит. Решение: когда у пользователя заканчивается дневной бесплатный лимит поисков, вместо предложения задонатить показывать обязательную разовую оплату — доступ без лимита на 24 часа за эквивалент ~10 шекелей.

Донат-кнопка в главном меню остаётся как отдельная опция для тех, кто хочет поддержать проект добровольно — это не заменяется, а дополняется новой платной опцией.

## Ценообразование

Оплата идёт через существующую инфраструктуру Telegram Stars (`currency="XTR"`, `provider_token=""`) — другого провайдера в проекте нет.

Курс Stars при покупке через Telegram (in-app, с наценкой Apple/Google ~30%) — примерно **$0.019–0.02 за звезду** (проверено через веб-поиск, июль 2026). 10 шекелей ≈ $2.7 (курс NIS/USD ~3.7). Отсюда:

```
$2.7 / $0.02 ≈ 135 звёзд
```

Округляем до **150 звёзд** (≈$3, ≤10 шек) — ближе к верхней границе диапазона, с запасом на дрейф курса.

Курс Stars не фиксирован в шекелях и может меняться — если разница станет заметной, значение константы `PAID_SEARCH_STARS` нужно будет поправить вручную (не автоматизируем конвертацию, т.к. в проекте нет источника живого курса NIS/USD/Stars).

## Константы

В `bot/limits.py`, рядом с существующими `FREE_DAILY_LIMIT` и `PREMIUM_DAYS`:

```python
PAID_SEARCH_STARS = 150
PAID_SEARCH_DAYS = 1
```

## Флоу

### 1. Показ paywall при исчерпании лимита

В `handle_city` ([bot/main.py:672-681](../../../bot/main.py#L672-L681)) при `allowed == False`:

- сохраняем `context.user_data["pending_city"] = city`
- вместо `_donate_kb(lang)` показываем новую клавиатуру `_paywall_kb(lang)` с одной кнопкой (`callback_data="buy_search_pass"`), без донат-кнопки рядом
- текст сообщения — новый ключ `paywall_text` вместо `rate_limit`

### 2. Покупка

Новый хендлер `cb_buy_search_pass` (аналог `cb_stars`, но с фиксированной ценой):

```python
async def cb_buy_search_pass(update, context):
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    await update.callback_query.message.reply_invoice(
        title=t(lang, "paywall_invoice_title"),
        description=t(lang, "paywall_invoice_desc"),
        payload="searchpass",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(t(lang, "paywall_invoice_title"), PAID_SEARCH_STARS)],
    )
```

Регистрация: `app.add_handler(CallbackQueryHandler(cb_buy_search_pass, pattern="^buy_search_pass$"))`.

### 3. Обработка оплаты

`successful_payment` ([bot/main.py:760-774](../../../bot/main.py#L760-L774)) начинает различать платежи по `update.message.successful_payment.invoice_payload`:

- **`payload == "searchpass"`**:
  1. `expiry = await grant_premium(user_id, days=PAID_SEARCH_DAYS)`
  2. лог `paid_access user=%d stars=%d` (по аналогии с текущим логом доната)
  3. инкремент статистики `paid_access_stars` (день + totals) — отдельно от `donations_stars`
  4. короткое сообщение `paywall_thanks` ("Готово, ищу {city}...")
  5. `city = context.user_data.pop("pending_city", None)`; если есть — сразу вызываем `_run_search(update, context, lang, city)` (см. рефакторинг ниже)
- **`payload.startswith("donate_")`**: текущее поведение без изменений.

### 4. Рефакторинг `handle_city`

Тело `handle_city` от строки 683 (после прохождения квоты: запуск `run_milonga_agent`, обработка timeout/error/not_found/result) выносится в отдельную функцию:

```python
async def _run_search(update, context, lang, city) -> None:
    ...
```

`handle_city` вызывает её после успешной проверки квоты; `successful_payment` вызывает её же после `grant_premium` при наличии `pending_city`.

## Локализация

В `bot/messages.py`, для всех языков (en/ru/he/es + текущий default), новые ключи по аналогии с существующими `donate_*`:

- `paywall_text` — сообщение при исчерпанном лимите, объясняющее разовую оплату за сутки безлимита
- `paywall_button` — подпись кнопки с ценой, например "150 ⭐ — доступ на сутки"
- `paywall_invoice_title` / `paywall_invoice_desc` — заголовок/описание инвойса
- `paywall_thanks` — сообщение сразу после оплаты, перед автопродолжением поиска

Существующие `donate_*` ключи и кнопка в главном меню не меняются.

## Статистика

В `get_search_stats()` ([bot/limits.py:132-178](../../../bot/limits.py#L132-L178)) добавляются поля `paid_access_stars_today` / `paid_access_stars_total`, по аналогии с `donations_stars_today` / `_total`. Позволяет в `/stats` видеть доход от платного доступа отдельно от добровольных донатов.

## Edge cases

- **Уже есть активный `premium_until`** (продлил ранее): `check_and_increment` возвращает `allowed=True` до проверки лимита — paywall не показывается, обычный флоу как сейчас.
- **Повторная оплата поверх активного дня**: `grant_premium` складывает дни поверх текущего `premium_until`, если он ещё не истёк — оплата просто продлевает доступ, это ожидаемо и безвредно.
- **Инвойс не оплачен / отменён**: `pending_city` остаётся в `context.user_data` до следующей успешной оплаты или пока не будет перезаписан новым городом при следующем paywall — на обычный (не paywall) поиск не влияет, читается только в `successful_payment`.
- **Перезапуск бота между инвойсом и оплатой**: `context.user_data` в памяти, без persistence (как и текущий `awaiting_stars`) — `pending_city` потеряется, после оплаты откроется безлимит, но автопродолжения поиска не будет (пользователь просто отправит город заново). Это соответствует текущему уровню надёжности кода и не требует Redis-хранилища для pending-состояния.

## Вне скоупа

- Конфигурируемая цена через env/конфиг-файл — отклонено, используем захардкоженную константу с ручной правкой при дрейфе курса.
- Изменение суммы/структуры доната — донат остаётся как есть.
- Persistence для `pending_city` в Redis — риск потери при рестарте признан приемлемым для масштаба проекта.
