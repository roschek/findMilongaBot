# Paid 24h Search Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the donate-only upsell shown when a user's daily free-search quota is exhausted with a mandatory one-time payment (150 Telegram Stars, ≈10 NIS) that unlocks unlimited searches for 24 hours and automatically continues the search that triggered the paywall.

**Architecture:** Reuse the existing Telegram Stars payment plumbing (`reply_invoice` / `PreCheckoutQueryHandler` / `filters.SUCCESSFUL_PAYMENT`) and the existing `grant_premium(user_id, days)` quota override in `bot/limits.py` (currently defined but never called). Add a new fixed-price invoice path parallel to the existing donate path, distinguished by `invoice_payload`. Extract the search-execution body of `handle_city` into a reusable `_run_search` helper so both the normal flow and the post-payment flow can call it.

**Tech Stack:** python-telegram-bot 22.7, Upstash Redis (via `app/redis_client.py`), pytest + pytest-asyncio (new, dev-only).

## Global Constraints

- Price: `PAID_SEARCH_STARS = 150` (Telegram Stars), `PAID_SEARCH_DAYS = 1` — from spec `docs/superpowers/specs/2026-07-16-paid-search-pass-design.md`.
- Payment provider: Telegram Stars only (`currency="XTR"`, `provider_token=""`) — no other provider exists in this project.
- The existing donate button/flow (`btn_donate`, `DONATE_TIERS`, `cb_donate`, `cb_stars`, `cb_custom_stars`) is untouched — it stays in the main menu.
- The paywall keyboard shown when the quota is exhausted shows **only** the buy-access button, no donate button.
- `pending_city` is stored in `context.user_data` (in-memory, no persistence) — consistent with the existing `awaiting_stars` pattern; no Redis-backed durability for this state (accepted risk, documented in the spec).
- No automated tests exist in this repo today (no pytest, no `tests/` dir) — this plan introduces pytest **only** for the new payload-branching / quota / invoice logic, not for pre-existing untested code (e.g. the search pipeline itself, `get_search_stats`, `cmd_stats`).

---

### Task 1: Add pytest test infrastructure

**Files:**
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Test: `tests/test_limits.py` (created in Task 2, first real test that exercises the harness)

**Interfaces:**
- Produces: a working `pytest` command that discovers async tests under `tests/` without requiring `@pytest.mark.asyncio` on every test (via `asyncio_mode = auto`).

- [ ] **Step 1: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.3
pytest-asyncio>=0.24
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Install dev dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: pytest and pytest-asyncio install without errors.

- [ ] **Step 4: Commit**

```bash
git add requirements-dev.txt pytest.ini
git commit -m "chore: add pytest dev dependencies for paid search pass tests"
```

(There is no test to run yet — Task 2 adds the first one and verifies the harness end-to-end.)

---

### Task 2: Add pricing constants and cover `grant_premium` for a 1-day pass

**Files:**
- Modify: `bot/limits.py:8-9` (add constants next to `FREE_DAILY_LIMIT` / `PREMIUM_DAYS`)
- Test: Create `tests/test_limits.py`

**Interfaces:**
- Produces: `bot.limits.PAID_SEARCH_STARS: int = 150`, `bot.limits.PAID_SEARCH_DAYS: int = 1`
- Consumes: `bot.limits.grant_premium(user_id: int, days: int = PREMIUM_DAYS) -> str` (already exists, unmodified)

- [ ] **Step 1: Add the constants**

In `bot/limits.py`, change:

```python
_DB_PATH = Path(__file__).parent.parent / "users_db.json"
FREE_DAILY_LIMIT = 5
PREMIUM_DAYS = 30
_REDIS_KEY = "users_db"
```

to:

```python
_DB_PATH = Path(__file__).parent.parent / "users_db.json"
FREE_DAILY_LIMIT = 5
PREMIUM_DAYS = 30
PAID_SEARCH_STARS = 150
PAID_SEARCH_DAYS = 1
_REDIS_KEY = "users_db"
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_limits.py`:

```python
from datetime import date, timedelta

import pytest

from bot import limits


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """Every test uses a throwaway file-fallback DB and never touches real Redis."""
    monkeypatch.setattr(limits, "_DB_PATH", tmp_path / "users_db.json")
    monkeypatch.setattr(limits, "_redis", lambda: None)


async def test_grant_premium_paid_search_pass_extends_one_day():
    expiry = await limits.grant_premium(123, days=limits.PAID_SEARCH_DAYS)
    assert expiry == str(date.today() + timedelta(days=1))


async def test_grant_premium_stacks_on_existing_pass():
    first_expiry = await limits.grant_premium(123, days=limits.PAID_SEARCH_DAYS)
    second_expiry = await limits.grant_premium(123, days=limits.PAID_SEARCH_DAYS)
    assert second_expiry == str(date.fromisoformat(first_expiry) + timedelta(days=1))


async def test_check_and_increment_allows_unlimited_after_paid_pass():
    await limits.grant_premium(123, days=limits.PAID_SEARCH_DAYS)
    allowed, remaining = await limits.check_and_increment(123)
    assert allowed is True
    assert remaining == -1
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_limits.py -v`
Expected: 3 passed (this also confirms the Task 1 harness works end-to-end — `grant_premium` and `check_and_increment` are pre-existing functions, so these tests should pass immediately once the constants exist).

- [ ] **Step 4: Commit**

```bash
git add bot/limits.py tests/test_limits.py
git commit -m "feat: add PAID_SEARCH_STARS/PAID_SEARCH_DAYS constants with coverage"
```

---

### Task 3: Extract `_run_search` out of `handle_city` (no behavior change)

**Files:**
- Modify: `bot/main.py:621-753` (`handle_city`)
- Test: Create `tests/test_main.py`

**Interfaces:**
- Produces: `async def _run_search(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, city: str, remaining: int) -> None` — runs the search, sends the "searching" status message, handles timeout/error/not-found/empty/ok outcomes, updates stats, and sends the final result message. `remaining` controls whether the "N searches left" hint is appended (`0 < remaining <= 2`); pass `-1` to suppress it (used after a paid pass, since the user is now unlimited).
- Consumes (unchanged from today): `run_milonga_agent`, `_format_events`, `_sources_line`, `_get_redis`, `_main_menu_kb`, `t`.

This task is a pure refactor: the body of `_run_search` is copied verbatim from the current `handle_city` (lines 683-753), with `remaining` becoming a parameter instead of a local variable computed from `check_and_increment`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_main.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import bot.main as main


def _make_update(text: str, user_id: int = 1, lang: str = "en"):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_user = MagicMock(id=user_id, language_code=lang)
    return update


def _make_context():
    context = MagicMock()
    context.user_data = {}
    return context


async def test_handle_city_delegates_to_run_search_with_remaining(monkeypatch):
    monkeypatch.setattr(main, "check_and_increment", AsyncMock(return_value=(True, 3)))
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_update("Berlin")
    context = _make_context()

    await main.handle_city(update, context)

    run_search_mock.assert_awaited_once_with(update, context, "en", "Berlin", 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `monkeypatch.setattr(main, "_run_search", ...)` raises `AttributeError: <module 'bot.main'> has no attribute '_run_search'`, since the function doesn't exist yet.

- [ ] **Step 3: Extract the function**

In `bot/main.py`, replace the tail of `handle_city` (from `logging.info("search_start"...)` through the final `await update.message.reply_text(...)` at the end of the function) with a call to a new helper, and define the helper right after `handle_city`.

`handle_city` becomes:

```python
async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    text = update.message.text.strip()

    # Partner flow: waiting for city input
    if context.user_data.get("partner_step") == "city":
        normalized = await normalize_partner_city(text)
        if normalized is None:
            await update.message.reply_text(t(lang, "partner_city_failed"), parse_mode="HTML")
            return  # keep partner_step = "city" so user can retry
        context.user_data["partner_city"] = normalized
        context.user_data["partner_step"] = "note"
        await update.message.reply_text(
            t(lang, "partner_ask_note"),
            parse_mode="HTML",
            reply_markup=_partner_note_kb(lang),
        )
        return

    # Partner flow: waiting for note input
    if context.user_data.get("partner_step") == "note":
        context.user_data.pop("partner_step")
        city = context.user_data.get("partner_city", "")
        await _finish_partner_request(update, context, city, note=text[:150])
        return

    # Handle custom Stars amount input
    if context.user_data.get("awaiting_stars"):
        context.user_data.pop("awaiting_stars")
        try:
            stars = int(text)
            if stars < 50:
                raise ValueError
        except ValueError:
            await update.message.reply_text(t(lang, "invalid_stars"), parse_mode="HTML")
            return
        await update.message.reply_invoice(
            title=t(lang, "donate_title"),
            description=t(lang, "donate_desc_tip"),
            payload=f"donate_{stars}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(t(lang, "donate_title"), stars)],
        )
        return

    city = text

    if context.user_data.get("searching"):
        return

    user_id = update.effective_user.id
    allowed, remaining = await check_and_increment(user_id)
    if not allowed:
        logging.info("rate_limit user=%d city=%r", user_id, city)
        await update.message.reply_text(
            t(lang, "rate_limit").format(limit=FREE_DAILY_LIMIT),
            parse_mode="HTML",
            reply_markup=_donate_kb(lang),
        )
        return

    await _run_search(update, context, lang, city, remaining)


async def _run_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, city: str, remaining: int
) -> None:
    user_id = update.effective_user.id
    logging.info("search_start user=%d city=%r lang=%s", user_id, city, lang)
    t0 = time.monotonic()

    context.user_data["searching"] = True
    status = await update.message.reply_text(
        t(lang, "searching").format(city=city),
        parse_mode="HTML",
    )

    try:
        result = await asyncio.wait_for(
            run_milonga_agent(city=city.title(), date=str(date.today())),
            timeout=270,
        )
    except asyncio.TimeoutError:
        logging.warning("search_timeout user=%d city=%r elapsed=%.0fs", user_id, city, time.monotonic() - t0)
        await status.edit_text(t(lang, "error"), parse_mode="HTML")
        context.user_data["searching"] = False
        return
    except Exception:
        logging.exception("search_error user=%d city=%r elapsed=%.0fs", user_id, city, time.monotonic() - t0)
        await status.edit_text(t(lang, "error"), parse_mode="HTML")
        context.user_data["searching"] = False
        return

    elapsed = time.monotonic() - t0
    context.user_data["searching"] = False

    if not result.city_found:
        logging.info("search_done user=%d city=%r result=not_found elapsed=%.0fs", user_id, city, elapsed)
        text = t(lang, "city_not_found").format(city=city)
        outcome = "result_notfound"
    elif result.events:
        logging.info("search_done user=%d city=%r result=ok events=%d elapsed=%.0fs",
                     user_id, result.city, len(result.events), elapsed)
        context.user_data["last_city"] = result.city
        text = _format_events(result.events, result.city, result.sources_checked)
        outcome = "result_ok"
    else:
        logging.info("search_done user=%d city=%r result=no_events elapsed=%.0fs", user_id, result.city, elapsed)
        context.user_data["last_city"] = result.city
        text = t(lang, "no_events").format(city=result.city)
        text += _sources_line(result.sources_checked)
        outcome = "result_empty"

    try:
        _r = _get_redis()
        if _r:
            _today = str(date.today())
            await _r.hincrby(f"stats:day:{_today}", outcome, 1)
            if result.city_found:
                await _r.zincrby("stats:cities", 1, result.city)
    except Exception:
        pass

    # Hint about remaining searches when running low (free users only)
    if 0 < remaining <= 2:
        text += t(lang, "searches_left").format(remaining=remaining)

    text += "\n\n" + t(lang, "disclaimer")

    try:
        await status.delete()
    except Exception:
        pass
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=_main_menu_kb(lang),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
```

(Note: the `rate_limit` text and `_donate_kb` keyboard here are still the *old* ones — Task 4 changes this specific branch. This task only extracts `_run_search` without changing behavior.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bot/main.py tests/test_main.py
git commit -m "refactor: extract _run_search out of handle_city"
```

---

### Task 4: Paywall keyboard + buy-access handler + quota-exceeded branch

**Files:**
- Modify: `bot/main.py` (imports, new `_paywall_kb`, new `cb_buy_search_pass`, `handle_city` quota-exceeded branch, handler registration)
- Modify: `bot/messages.py` (new keys, all 4 languages — content in Task 6, but the keys must exist before this task's tests can pass, so add the **English** entries now and the rest in Task 6; see note in Step 1)
- Test: `tests/test_main.py` (append)

**Interfaces:**
- Produces: `_paywall_kb(lang: str) -> InlineKeyboardMarkup` (single button, `callback_data="buy_search_pass"`), `async def cb_buy_search_pass(update, context) -> None`.
- Consumes: `PAID_SEARCH_STARS` (Task 2), `t`, `_lang`.

- [ ] **Step 1: Add English message keys needed by this task**

In `bot/messages.py`, inside `MSG["en"]`, add these new keys right after `"donate_thanks"` (exact placement doesn't matter, just group them together):

```python
        "paywall_button": "🔓 Unlock 24h — {stars} ⭐",
        "paywall_invoice_title": "24-hour unlimited access",
        "paywall_invoice_desc": "Unlock unlimited milonga searches for 24 hours",
```

(The `ru`/`he`/`es` translations and the `paywall_thanks` / `paywall_unlocked` keys used by `successful_payment` are added in Task 6. Adding only English here keeps this task's tests runnable without blocking on translation work; the bot already falls back to English via `t()`'s `MSG.get(lang, MSG["en"])` for any language whose dict doesn't yet have a key, so nothing breaks for `ru`/`he`/`es` users in the meantime.)

- [ ] **Step 2: Add the constant import, keyboard, and callback handler**

In `bot/main.py`, change the limits import:

```python
from bot.limits import check_and_increment, get_status, get_search_stats, FREE_DAILY_LIMIT
```

to:

```python
from bot.limits import (
    check_and_increment,
    get_status,
    get_search_stats,
    grant_premium,
    FREE_DAILY_LIMIT,
    PAID_SEARCH_STARS,
    PAID_SEARCH_DAYS,
)
```

Add `_paywall_kb` right after `_donate_kb` (around line 79):

```python
def _paywall_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            t(lang, "paywall_button").format(stars=PAID_SEARCH_STARS),
            callback_data="buy_search_pass",
        )
    ]])
```

Add `cb_buy_search_pass` right after `cb_stars` (around line 238):

```python
async def cb_buy_search_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

- [ ] **Step 3: Update the quota-exceeded branch in `handle_city`**

Change:

```python
    allowed, remaining = await check_and_increment(user_id)
    if not allowed:
        logging.info("rate_limit user=%d city=%r", user_id, city)
        await update.message.reply_text(
            t(lang, "rate_limit").format(limit=FREE_DAILY_LIMIT),
            parse_mode="HTML",
            reply_markup=_donate_kb(lang),
        )
        return
```

to:

```python
    allowed, remaining = await check_and_increment(user_id)
    if not allowed:
        logging.info("rate_limit user=%d city=%r", user_id, city)
        context.user_data["pending_city"] = city
        await update.message.reply_text(
            t(lang, "rate_limit").format(limit=FREE_DAILY_LIMIT, stars=PAID_SEARCH_STARS),
            parse_mode="HTML",
            reply_markup=_paywall_kb(lang),
        )
        return
```

- [ ] **Step 4: Register the new callback handler**

In `main()`, right after the line registering `cb_stars`:

```python
    app.add_handler(CallbackQueryHandler(cb_stars, pattern=r"^stars_\d+$"))
```

add:

```python
    app.add_handler(CallbackQueryHandler(cb_buy_search_pass, pattern="^buy_search_pass$"))
```

- [ ] **Step 5: Write the failing tests**

Append to `tests/test_main.py`:

```python
async def test_handle_city_quota_exceeded_saves_pending_city_and_shows_paywall(monkeypatch):
    monkeypatch.setattr(main, "check_and_increment", AsyncMock(return_value=(False, 0)))

    update = _make_update("Berlin")
    context = _make_context()

    await main.handle_city(update, context)

    assert context.user_data["pending_city"] == "Berlin"
    update.message.reply_text.assert_awaited_once()
    _, kwargs = update.message.reply_text.call_args
    kb = kwargs["reply_markup"]
    assert kb.inline_keyboard[0][0].callback_data == "buy_search_pass"


async def test_cb_buy_search_pass_sends_invoice_with_fixed_price():
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.reply_invoice = AsyncMock()
    update.effective_user = MagicMock(language_code="en")
    context = _make_context()

    await main.cb_buy_search_pass(update, context)

    update.callback_query.message.reply_invoice.assert_awaited_once()
    _, kwargs = update.callback_query.message.reply_invoice.call_args
    assert kwargs["payload"] == "searchpass"
    assert kwargs["currency"] == "XTR"
    assert kwargs["prices"][0].amount == main.PAID_SEARCH_STARS
```

- [ ] **Step 6: Run tests to verify they fail, then pass**

Run: `pytest tests/test_main.py -v`
Expected before Steps 1-4: FAIL (`_paywall_kb`/`cb_buy_search_pass` don't exist).
Expected after Steps 1-4: all tests in `tests/test_main.py` PASS (4 total so far).

- [ ] **Step 7: Commit**

```bash
git add bot/main.py bot/messages.py tests/test_main.py
git commit -m "feat: paywall keyboard and fixed-price invoice for 24h search pass"
```

---

### Task 5: Branch `successful_payment` on invoice payload

**Files:**
- Modify: `bot/main.py:760-774` (`successful_payment`)
- Test: `tests/test_main.py` (append)

**Interfaces:**
- Consumes: `grant_premium(user_id: int, days: int) -> str` (Task 2/existing), `_run_search(update, context, lang, city, remaining)` (Task 3), `PAID_SEARCH_STARS`, `PAID_SEARCH_DAYS`.
- Behavior contract: payload `"searchpass"` grants `PAID_SEARCH_DAYS` of premium, then either continues the search that triggered the paywall (if `pending_city` is present) or shows an "unlocked" confirmation (if not — e.g. bot restarted between invoice and payment). Any other payload (the existing `donate_{stars}` shape) keeps today's exact behavior.

- [ ] **Step 1: Add English message keys for this task**

In `bot/messages.py`, inside `MSG["en"]`, add (grouped with the Task 4 additions):

```python
        "paywall_thanks": "✅ Unlimited access unlocked for 24 hours!\nSearching in <b>{city}</b>…",
        "paywall_unlocked": "✅ Unlimited access unlocked for 24 hours! Send me a city to search.",
```

- [ ] **Step 2: Update `successful_payment`**

Replace:

```python
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    stars = update.message.successful_payment.total_amount
    logging.info("donation user=%d stars=%d", update.effective_user.id, stars)
    try:
        _r = _get_redis()
        if _r:
            _today = str(date.today())
            await _r.hincrby(f"stats:day:{_today}", "donations_stars", stars)
            await _r.hincrby("stats:totals", "donations_stars", stars)
    except Exception:
        pass
    await update.message.reply_text(
        t(lang, "donate_thanks"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
    )
```

with:

```python
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    payload = update.message.successful_payment.invoice_payload
    stars = update.message.successful_payment.total_amount
    user_id = update.effective_user.id

    if payload == "searchpass":
        logging.info("paid_access user=%d stars=%d", user_id, stars)
        await grant_premium(user_id, days=PAID_SEARCH_DAYS)
        try:
            _r = _get_redis()
            if _r:
                _today = str(date.today())
                await _r.hincrby(f"stats:day:{_today}", "paid_access_stars", stars)
                await _r.hincrby("stats:totals", "paid_access_stars", stars)
        except Exception:
            pass

        city = context.user_data.pop("pending_city", None)
        if city:
            await update.message.reply_text(
                t(lang, "paywall_thanks").format(city=city), parse_mode="HTML"
            )
            await _run_search(update, context, lang, city, -1)
        else:
            await update.message.reply_text(
                t(lang, "paywall_unlocked"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
            )
        return

    logging.info("donation user=%d stars=%d", user_id, stars)
    try:
        _r = _get_redis()
        if _r:
            _today = str(date.today())
            await _r.hincrby(f"stats:day:{_today}", "donations_stars", stars)
            await _r.hincrby("stats:totals", "donations_stars", stars)
    except Exception:
        pass
    await update.message.reply_text(
        t(lang, "donate_thanks"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
    )
```

- [ ] **Step 3: Write the failing tests**

Append to `tests/test_main.py`:

```python
def _make_payment_update(payload: str, stars: int, user_id: int = 1, lang: str = "en"):
    update = MagicMock()
    update.effective_user = MagicMock(id=user_id, language_code=lang)
    update.message.successful_payment.invoice_payload = payload
    update.message.successful_payment.total_amount = stars
    update.message.reply_text = AsyncMock()
    return update


async def test_successful_payment_searchpass_continues_pending_search(monkeypatch):
    monkeypatch.setattr(main, "grant_premium", AsyncMock(return_value="2026-07-17"))
    monkeypatch.setattr(main, "_get_redis", lambda: None)
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_payment_update("searchpass", main.PAID_SEARCH_STARS)
    context = _make_context()
    context.user_data["pending_city"] = "Berlin"

    await main.successful_payment(update, context)

    main.grant_premium.assert_awaited_once_with(1, days=main.PAID_SEARCH_DAYS)
    run_search_mock.assert_awaited_once_with(update, context, "en", "Berlin", -1)
    assert "pending_city" not in context.user_data


async def test_successful_payment_searchpass_without_pending_city_shows_unlocked(monkeypatch):
    monkeypatch.setattr(main, "grant_premium", AsyncMock(return_value="2026-07-17"))
    monkeypatch.setattr(main, "_get_redis", lambda: None)
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_payment_update("searchpass", main.PAID_SEARCH_STARS)
    context = _make_context()

    await main.successful_payment(update, context)

    run_search_mock.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "paywall_unlocked")


async def test_successful_payment_donate_payload_keeps_existing_behavior(monkeypatch):
    grant_premium_mock = AsyncMock()
    monkeypatch.setattr(main, "grant_premium", grant_premium_mock)
    monkeypatch.setattr(main, "_get_redis", lambda: None)
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_payment_update("donate_250", 250)
    context = _make_context()

    await main.successful_payment(update, context)

    grant_premium_mock.assert_not_awaited()
    run_search_mock.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert args[0] == main.t("en", "donate_thanks")
    assert kwargs["reply_markup"] is not None
```

- [ ] **Step 4: Run tests to verify they fail, then pass**

Run: `pytest tests/test_main.py -v`
Expected before Step 2: FAIL (`grant_premium` not called, `pending_city` not consumed, `_run_search` not invoked).
Expected after Step 2: all tests in `tests/test_main.py` PASS (7 total so far).

- [ ] **Step 5: Commit**

```bash
git add bot/main.py bot/messages.py tests/test_main.py
git commit -m "feat: grant paid access and auto-continue search on successful payment"
```

---

### Task 6: Full localization (ru / he / es) + regression test for message completeness

**Files:**
- Modify: `bot/messages.py` (add the 5 new keys to `MSG["ru"]`, `MSG["he"]`, `MSG["es"]`; update `rate_limit` in all 4 languages to mention the price)
- Test: Create `tests/test_messages.py`

**Interfaces:**
- No new functions — this task only adds/edits string data. The regression test guards against a language dict missing one of the new keys (which would silently fall back to English via `t()`, going unnoticed until a non-English user hits the flow).

- [ ] **Step 1: Update `rate_limit` in all 4 languages to mention the price**

In `bot/messages.py`, `MSG["en"]["rate_limit"]`, change:

```python
        "rate_limit": (
            "⏳ You've used all {limit} free searches for today.\n\n"
            "Support the project to unlock unlimited searches! ☕"
        ),
```

to:

```python
        "rate_limit": (
            "⏳ You've used all {limit} free searches for today.\n\n"
            "Unlock unlimited searches for 24 hours for {stars} ⭐."
        ),
```

`MSG["ru"]["rate_limit"]`, change:

```python
        "rate_limit": (
            "⏳ Вы использовали все {limit} бесплатных поиска сегодня.\n\n"
            "Поддержите проект и получите безлимитный поиск! ☕"
        ),
```

to:

```python
        "rate_limit": (
            "⏳ Вы использовали все {limit} бесплатных поиска сегодня.\n\n"
            "Откройте безлимит на 24 часа за {stars} ⭐."
        ),
```

`MSG["he"]["rate_limit"]`, change:

```python
        "rate_limit": (
            "⏳ השתמשת בכל {limit} החיפושים החינמיים של היום.\n\n"
            "תמוך בפרויקט וקבל חיפוש ללא הגבלה! ☕"
        ),
```

to:

```python
        "rate_limit": (
            "⏳ השתמשת בכל {limit} החיפושים החינמיים של היום.\n\n"
            "פתח חיפוש ללא הגבלה ל-24 שעות תמורת {stars} ⭐."
        ),
```

`MSG["es"]["rate_limit"]`, change:

```python
        "rate_limit": (
            "⏳ Has usado las {limit} búsquedas gratuitas de hoy.\n\n"
            "¡Apoya el proyecto y desbloquea búsquedas ilimitadas! ☕"
        ),
```

to:

```python
        "rate_limit": (
            "⏳ Has usado las {limit} búsquedas gratuitas de hoy.\n\n"
            "Desbloquea búsquedas ilimitadas por 24 horas por {stars} ⭐."
        ),
```

- [ ] **Step 2: Add the 5 new keys to `MSG["ru"]`**

Insert right after `"donate_thanks"` in `MSG["ru"]`:

```python
        "paywall_button": "🔓 Открыть на сутки — {stars} ⭐",
        "paywall_invoice_title": "Безлимит на 24 часа",
        "paywall_invoice_desc": "Безлимитный поиск милонг в течение 24 часов",
        "paywall_thanks": "✅ Безлимит открыт на 24 часа!\nИщу в <b>{city}</b>…",
        "paywall_unlocked": "✅ Безлимит открыт на 24 часа! Отправьте город для поиска.",
```

- [ ] **Step 3: Add the 5 new keys to `MSG["he"]`**

Insert right after `"donate_thanks"` in `MSG["he"]`:

```python
        "paywall_button": "🔓 פתח ל-24 שעות — {stars} ⭐",
        "paywall_invoice_title": "גישה ללא הגבלה ל-24 שעות",
        "paywall_invoice_desc": "פתח חיפוש מילונגות ללא הגבלה למשך 24 שעות",
        "paywall_thanks": "✅ הגישה נפתחה ל-24 שעות!\nמחפש ב-<b>{city}</b>…",
        "paywall_unlocked": "✅ הגישה נפתחה ל-24 שעות! שלח שם עיר לחיפוש.",
```

- [ ] **Step 4: Add the 5 new keys to `MSG["es"]`**

Insert right after `"donate_thanks"` in `MSG["es"]`:

```python
        "paywall_button": "🔓 Desbloquear 24h — {stars} ⭐",
        "paywall_invoice_title": "Acceso ilimitado por 24 horas",
        "paywall_invoice_desc": "Desbloquea búsquedas ilimitadas de milongas por 24 horas",
        "paywall_thanks": "✅ ¡Acceso ilimitado desbloqueado por 24 horas!\nBuscando en <b>{city}</b>…",
        "paywall_unlocked": "✅ ¡Acceso ilimitado desbloqueado por 24 horas! Envíame una ciudad para buscar.",
```

- [ ] **Step 5: Write the failing test**

Create `tests/test_messages.py`:

```python
import pytest

from bot.messages import MSG

NEW_KEYS = [
    "paywall_button",
    "paywall_invoice_title",
    "paywall_invoice_desc",
    "paywall_thanks",
    "paywall_unlocked",
]


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
@pytest.mark.parametrize("key", NEW_KEYS)
def test_paywall_key_present_and_non_empty(lang, key):
    assert MSG[lang].get(key), f"MSG['{lang}']['{key}'] is missing or empty"


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
def test_rate_limit_mentions_price_placeholder(lang):
    assert "{stars}" in MSG[lang]["rate_limit"]
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_messages.py -v`
Expected: FAIL on `ru`/`he`/`es` (`paywall_*` keys not present in those dicts yet, `{stars}` not yet in their `rate_limit`) — run this *before* Steps 1-4 to confirm the gap, or trust the "before/after" framing if applying steps in order.

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_messages.py -v`
Expected: 24 passed (5 keys × 4 langs + 4 rate_limit checks).

- [ ] **Step 8: Run the full test suite**

Run: `pytest -v`
Expected: all tests across `tests/test_limits.py`, `tests/test_main.py`, `tests/test_messages.py` PASS.

- [ ] **Step 9: Commit**

```bash
git add bot/messages.py tests/test_messages.py
git commit -m "feat: localize paywall messages for ru/he/es and guard against missing keys"
```

---

### Task 7: Admin stats visibility for paid access revenue

**Files:**
- Modify: `bot/limits.py:132-178` (`get_search_stats`)
- Modify: `bot/main.py:154-181` (`cmd_stats`)

**Interfaces:**
- Produces: `get_search_stats()` return dict gains `"paid_access_stars_today": int` and `"paid_access_stars_total": int`, mirroring the existing `donations_stars_today`/`donations_stars_total` fields.
- No test — this mirrors the existing untested `donations_stars_*` fields exactly (same pattern, same risk profile); adding a test here would test Redis plumbing already exercised by the untested sibling fields, which is out of scope per the "pytest only for the new payload/quota/invoice logic" decision.

- [ ] **Step 1: Add the fields to the `base` dict in `get_search_stats`**

In `bot/limits.py`, change:

```python
    base = {
        "total_users": total_users,
        "active_today": 0,
        "new_users_today": 0,
        "searches_today": 0,
        "result_ok": 0,
        "result_empty": 0,
        "result_notfound": 0,
        "partner_requests_today": 0,
        "donations_stars_today": 0,
        "searches_total": 0,
        "donations_stars_total": 0,
        "partner_requests_total": 0,
        "top_cities": [],
    }
```

to:

```python
    base = {
        "total_users": total_users,
        "active_today": 0,
        "new_users_today": 0,
        "searches_today": 0,
        "result_ok": 0,
        "result_empty": 0,
        "result_notfound": 0,
        "partner_requests_today": 0,
        "donations_stars_today": 0,
        "paid_access_stars_today": 0,
        "searches_total": 0,
        "donations_stars_total": 0,
        "paid_access_stars_total": 0,
        "partner_requests_total": 0,
        "top_cities": [],
    }
```

- [ ] **Step 2: Populate the fields from Redis in the same function**

In `bot/limits.py`, change the `return` inside the `try` block of `get_search_stats` from:

```python
        return {
            "total_users": total_users,
            "active_today": _i(day_raw, "active"),
            "new_users_today": _i(day_raw, "new_users"),
            "searches_today": _i(day_raw, "searches"),
            "result_ok": _i(day_raw, "result_ok"),
            "result_empty": _i(day_raw, "result_empty"),
            "result_notfound": _i(day_raw, "result_notfound"),
            "partner_requests_today": _i(day_raw, "partner_requests"),
            "donations_stars_today": _i(day_raw, "donations_stars"),
            "searches_total": _i(totals_raw, "searches"),
            "donations_stars_total": _i(totals_raw, "donations_stars"),
            "partner_requests_total": _i(totals_raw, "partner_requests"),
            "top_cities": [(c, int(s)) for c, s in cities_raw],
        }
```

to:

```python
        return {
            "total_users": total_users,
            "active_today": _i(day_raw, "active"),
            "new_users_today": _i(day_raw, "new_users"),
            "searches_today": _i(day_raw, "searches"),
            "result_ok": _i(day_raw, "result_ok"),
            "result_empty": _i(day_raw, "result_empty"),
            "result_notfound": _i(day_raw, "result_notfound"),
            "partner_requests_today": _i(day_raw, "partner_requests"),
            "donations_stars_today": _i(day_raw, "donations_stars"),
            "paid_access_stars_today": _i(day_raw, "paid_access_stars"),
            "searches_total": _i(totals_raw, "searches"),
            "donations_stars_total": _i(totals_raw, "donations_stars"),
            "paid_access_stars_total": _i(totals_raw, "paid_access_stars"),
            "partner_requests_total": _i(totals_raw, "partner_requests"),
            "top_cities": [(c, int(s)) for c, s in cities_raw],
        }
```

- [ ] **Step 3: Show it in `/stats`**

In `bot/main.py`, change the `cmd_stats` message from:

```python
        f"⭐ <b>Donations</b>\n"
        f"  Today: {s['donations_stars_today']}  |  All time: {s['donations_stars_total']}\n\n"
        f"🔝 <b>Top cities</b>\n{cities_lines}",
```

to:

```python
        f"⭐ <b>Donations</b>\n"
        f"  Today: {s['donations_stars_today']}  |  All time: {s['donations_stars_total']}\n\n"
        f"🔓 <b>Paid access</b>\n"
        f"  Today: {s['paid_access_stars_today']} ⭐  |  All time: {s['paid_access_stars_total']} ⭐\n\n"
        f"🔝 <b>Top cities</b>\n{cities_lines}",
```

- [ ] **Step 4: Run the full test suite to confirm no regression**

Run: `pytest -v`
Expected: all tests still PASS (this task adds no new tests, per the note above).

- [ ] **Step 5: Commit**

```bash
git add bot/limits.py bot/main.py
git commit -m "feat: show paid access revenue separately from donations in /stats"
```

---

### Task 8: Manual verification (real Telegram Stars payment)

This task has no code changes — it's a pre-deploy checklist, because Telegram Stars payments cannot be exercised by unit tests (they require a real Telegram client and a real `PreCheckoutQuery`/`SUCCESSFUL_PAYMENT` update from Telegram's servers).

- [ ] **Step 1: Deploy to a test bot or the existing bot in a low-traffic window**

- [ ] **Step 2: Manually exhaust the free quota**

Send `FREE_DAILY_LIMIT` (5) different city searches from a test Telegram account. Confirm the 6th attempt shows the new paywall message with **only** the "Unlock 24h — 150 ⭐" button (no donate button).

- [ ] **Step 3: Pay with Telegram Stars**

Tap the button, confirm the Telegram-native Stars payment sheet shows "24-hour unlimited access" for 150 ⭐, and complete the payment (Telegram Stars payments in a real bot are real — use a small test account you control, since Stars have real monetary value).

- [ ] **Step 4: Confirm auto-continuation**

Confirm the bot sends the "unlocked" thank-you message, then automatically searches the city that triggered the paywall (the 6th city from Step 2) without requiring you to resend it.

- [ ] **Step 5: Confirm unlimited access**

Send 2-3 more different cities immediately after. Confirm none of them hit the paywall (premium is active).

- [ ] **Step 6: Confirm `/stats` reflects the payment**

As the admin account (`ADMIN_ID`), run `/stats` and confirm the new "Paid access" line shows 150 ⭐ today and all-time, separate from "Donations".

- [ ] **Step 7: Confirm the donate flow is unaffected**

From the main menu, tap "Support the project", pick a tier (e.g. 50 ⭐), pay, and confirm the existing thank-you message and behavior are unchanged.
