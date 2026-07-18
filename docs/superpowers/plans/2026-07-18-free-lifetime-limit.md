# Free Tier: 1 Lifetime Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 5-searches-per-day free tier with exactly one free search per user, ever. After that one search, every subsequent search always requires the existing 150 ⭐ / 24h paid pass (no recurring free allowance, including after a paid pass expires).

**Architecture:** Replace the day-scoped Redis counter (`rl:{user_id}:{date}`, TTL to midnight) with a membership check against the existing `stats:known_users` Redis set — already populated on every user's first-ever search for stats purposes, now reused as the source of truth for "has this user already spent their one free search." No migration step is needed: existing users are already members of that set. The file-fallback (local dev, no Redis) mirrors this with a boolean `free_used` flag per user in the same JSON blob used for `premium_until`.

**Tech Stack:** Same as the existing codebase (python-telegram-bot, Upstash Redis via `app/redis_client.py`, pytest + pytest-asyncio for tests).

## Global Constraints

- Exactly **1** free search per user, for the lifetime of the account — not per day. From `docs/superpowers/specs/2026-07-18-free-lifetime-limit-design.md`.
- **No migration script.** `stats:known_users` already contains every user who has ever searched (populated unconditionally on first search, independent of whether that search was allowed). Reusing it as the gating source of truth handles existing users automatically.
- **After a paid 24h pass expires, the user does NOT get a new free search.** They return to "free search already used" and must pay again. The product has no recurring free tier after the first search.
- The `FREE_DAILY_LIMIT` constant is **removed entirely**, not renamed — the new gate is binary (has-searched-before / has-not), not a numeric threshold, so a numeric constant would be unused dead code.
- `check_and_increment`'s return contract changes meaning but keeps its shape: `(allowed: bool, remaining: int)` where `remaining` is `-1` for premium/unlimited, `0` otherwise (whether the free search was just granted or is already exhausted — the two cases are disambiguated by `allowed`, and `_run_search`'s only consumer of `remaining` never receives an ambiguous positive value under the new model).
- A new daily Redis set `stats:active_users:{date}` is introduced purely for the admin `/stats` "active today" metric — the old day-scoped `rl:` counter (which incidentally doubled as the "first search of the day" signal for that metric) is gone, so this replaces it. This does not change `/stats`' output shape (`get_search_stats()` still reads the `"active"` field from `stats:day:{date}`), only how that field gets incremented.
- Existing `pytest.ini` (`asyncio_mode = auto`) and dev dependencies (`requirements-dev.txt`) from the prior paid-search-pass plan already cover this work — no new test infra needed.

---

### Task 1: Rewrite `bot/limits.py` gating logic

**Files:**
- Modify: `bot/limits.py` (remove `FREE_DAILY_LIMIT`, rewrite `check_and_increment`, rewrite `get_status`)
- Test: Modify `tests/test_limits.py` (append; keep the 3 existing tests, which only exercise `grant_premium` and the premium branch of `check_and_increment` and remain valid unchanged)

**Interfaces:**
- Produces: `check_and_increment(user_id: int) -> tuple[bool, int]` — same signature, new semantics (see Global Constraints). `get_status(user_id: int) -> dict` — same signature, `"remaining"` is now `1` (free search available), `0` (free search used), or `-1` (premium).
- Consumes: `_redis()`, `_load()`, `_save()`, `_entry()`, `_ttl_until_midnight()` — all pre-existing, unchanged.

- [ ] **Step 1: Write the failing tests**

Read the current `tests/test_limits.py` first — it has 3 existing tests (`grant_premium`/premium-branch tests) plus an `isolate_storage` autouse fixture that forces the file-fallback path (`_redis` patched to return `None`). Keep that fixture and those 3 tests exactly as they are. Append the following to the same file (after the existing tests, before or after doesn't matter — keep the file's structure otherwise intact):

```python
class FakeRedis:
    """Minimal in-memory double for the subset of the Upstash Redis async API
    bot/limits.py uses: get/set (users_db blob), sismember/sadd (known-users
    gate), hincrby/expire (stats bookkeeping)."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._sets: dict[str, set[str]] = {}
        self._hashes: dict[str, dict[str, int]] = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value):
        self._store[key] = value

    async def sismember(self, key, member):
        return member in self._sets.get(key, set())

    async def sadd(self, key, member):
        members = self._sets.setdefault(key, set())
        if member in members:
            return 0
        members.add(member)
        return 1

    async def hincrby(self, key, field, amount):
        h = self._hashes.setdefault(key, {})
        h[field] = h.get(field, 0) + amount
        return h[field]

    async def expire(self, key, seconds):
        return True


async def test_check_and_increment_file_fallback_allows_one_free_search_then_blocks():
    first_allowed, first_remaining = await limits.check_and_increment(123)
    second_allowed, second_remaining = await limits.check_and_increment(123)

    assert (first_allowed, first_remaining) == (True, 0)
    assert (second_allowed, second_remaining) == (False, 0)


async def test_get_status_file_fallback_reflects_free_used():
    before = await limits.get_status(123)
    await limits.check_and_increment(123)
    after = await limits.get_status(123)

    assert before == {"premium": False, "premium_until": None, "remaining": 1}
    assert after == {"premium": False, "premium_until": None, "remaining": 0}


async def test_check_and_increment_redis_allows_first_ever_search_then_blocks(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limits, "_redis", lambda: fake)

    first_allowed, first_remaining = await limits.check_and_increment(456)
    second_allowed, second_remaining = await limits.check_and_increment(456)

    assert (first_allowed, first_remaining) == (True, 0)
    assert (second_allowed, second_remaining) == (False, 0)
    assert await fake.sismember("stats:known_users", "456") is True


async def test_check_and_increment_redis_known_user_gets_unlimited_after_paid_pass(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limits, "_redis", lambda: fake)

    await limits.check_and_increment(456)  # spends the one free search, becomes "known"
    blocked_allowed, blocked_remaining = await limits.check_and_increment(456)
    assert (blocked_allowed, blocked_remaining) == (False, 0)

    await limits.grant_premium(456, days=limits.PAID_SEARCH_DAYS)
    allowed, remaining = await limits.check_and_increment(456)

    assert (allowed, remaining) == (True, -1)


async def test_get_status_redis_reflects_known_users(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limits, "_redis", lambda: fake)

    before = await limits.get_status(456)
    await limits.check_and_increment(456)
    after = await limits.get_status(456)

    assert before == {"premium": False, "premium_until": None, "remaining": 1}
    assert after == {"premium": False, "premium_until": None, "remaining": 0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_limits.py -v`
Expected: FAIL — the new tests assert behavior (`(True, 0)` then `(False, 0)` for a lifetime limit) that the current 5-per-day implementation doesn't produce (it would allow 5 searches, not 1, and `remaining` would count down from 4 rather than jumping straight to blocked).

- [ ] **Step 3: Rewrite `check_and_increment` and `get_status`**

In `bot/limits.py`, remove line 8 (`FREE_DAILY_LIMIT = 5`) entirely — the file's constants become:

```python
_DB_PATH = Path(__file__).parent.parent / "users_db.json"
PREMIUM_DAYS = 30
PAID_SEARCH_STARS = 150
PAID_SEARCH_DAYS = 1
_REDIS_KEY = "users_db"
```

Replace the entire `check_and_increment` function with:

```python
async def check_and_increment(user_id: int) -> tuple[bool, int]:
    """
    Returns (allowed, remaining).
    remaining = -1 means premium (unlimited); 0 means the one lifetime free
    search was just granted (allowed=True) or is already exhausted (allowed=False).
    """
    today = str(date.today())
    r = _redis()

    if r:
        try:
            # Check premium via users_db blob
            data = await _load()
            premium_until = data.get(str(user_id), {}).get("premium_until")
            if premium_until and premium_until >= today:
                return True, -1

            is_known = await r.sismember("stats:known_users", str(user_id))
            allowed = not is_known
        except Exception:
            pass
        else:
            # Non-critical stats — isolated so failures never affect the gating result
            try:
                day_key = f"stats:day:{today}"
                await r.hincrby(day_key, "searches", 1)
                await r.hincrby("stats:totals", "searches", 1)

                active_key = f"stats:active_users:{today}"
                active_added = await r.sadd(active_key, str(user_id))
                if active_added == 1:
                    await r.hincrby(day_key, "active", 1)
                    await r.expire(active_key, _ttl_until_midnight() + 86400)
                    # Keep day key for ~2 days so yesterday's stats survive past midnight
                    await r.expire(day_key, _ttl_until_midnight() + 86400)

                known_added = await r.sadd("stats:known_users", str(user_id))
                if known_added == 1:
                    await r.hincrby(day_key, "new_users", 1)
            except Exception:
                pass
            return allowed, 0

    # File fallback (local dev — sequential PTB updates, no race condition in practice)
    data = await _load()
    entry = _entry(data, user_id)

    premium_until = entry.get("premium_until")
    if premium_until and premium_until >= today:
        return True, -1

    if entry.get("free_used"):
        return False, 0

    entry["free_used"] = True
    await _save(data)
    return True, 0
```

Replace the entire `get_status` function with:

```python
async def get_status(user_id: int) -> dict:
    """Returns {"premium": bool, "premium_until": str|None, "remaining": int}.
    remaining: -1 = premium (unlimited), 1 = free search still available, 0 = free search used.
    """
    data = await _load()
    entry = data.get(str(user_id), {})
    today = str(date.today())
    premium_until = entry.get("premium_until")
    is_premium = bool(premium_until and premium_until >= today)
    if is_premium:
        return {"premium": True, "premium_until": premium_until, "remaining": -1}
    r = _redis()
    if r:
        try:
            is_known = await r.sismember("stats:known_users", str(user_id))
            return {"premium": False, "premium_until": None, "remaining": 0 if is_known else 1}
        except Exception:
            pass
    free_used = bool(entry.get("free_used"))
    return {"premium": False, "premium_until": premium_until, "remaining": 0 if free_used else 1}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_limits.py -v`
Expected: all tests in `tests/test_limits.py` PASS (9 total: 3 pre-existing + 6 new).

- [ ] **Step 5: Commit**

```bash
git add bot/limits.py tests/test_limits.py
git commit -m "feat: gate free search on lifetime known_users membership instead of daily counter"
```

---

### Task 2: Update `bot/main.py` call sites (`cmd_status`, quota-exceeded branch, free-trial notice)

**Files:**
- Modify: `bot/main.py` (import, `cmd_status`, `handle_city`'s quota-exceeded branch, `_run_search`'s hint)
- Modify: `bot/messages.py` (English-only: new `status_free_available`, `status_free_used`, `free_trial_used` keys; reworded `rate_limit`; remove now-dead `status_free`/`searches_left` from `MSG["en"]` — ru/he/es cleanup happens in Task 3)
- Test: Modify `tests/test_main.py` (append)

**Interfaces:**
- Consumes: `get_status(user_id) -> dict` and `check_and_increment(user_id) -> (bool, int)` from Task 1 (already committed).
- No new functions produced — this task only changes call sites and message keys.

- [ ] **Step 1: Update English message keys in `bot/messages.py`**

In `MSG["en"]`, replace:

```python
        "rate_limit": (
            "⏳ You've used all {limit} free searches for today.\n\n"
            "Unlock unlimited searches for 24 hours for {stars} ⭐."
        ),
        "premium_granted": (
            "🎉 Thank you! Unlimited searches unlocked for <b>{days} days</b> (until {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Status:</b> Premium until <b>{until}</b>. Unlimited searches.",
        "status_free": "🔍 <b>Status:</b> Free plan — <b>{remaining}</b> of {limit} searches left today.",
        "searches_left": "\n<i>({remaining} free search(es) left today)</i>",
```

with:

```python
        "rate_limit": (
            "⏳ Your one free trial search is already used.\n\n"
            "Unlock unlimited searches for 24 hours for {stars} ⭐."
        ),
        "premium_granted": (
            "🎉 Thank you! Unlimited searches unlocked for <b>{days} days</b> (until {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Status:</b> Premium until <b>{until}</b>. Unlimited searches.",
        "status_free_available": "🔍 <b>Status:</b> You have your one free trial search available.",
        "status_free_used": "🔍 <b>Status:</b> Free trial search already used. Unlock 24h unlimited for {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ That was your one free trial search. Next time, unlock 24h unlimited for {stars} ⭐.</i>",
```

(`premium_granted` is untouched — it's pre-existing dead code unrelated to this task, left as-is.)

- [ ] **Step 2: Update the `bot.limits` import in `bot/main.py`**

Change:

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

to:

```python
from bot.limits import (
    check_and_increment,
    get_status,
    get_search_stats,
    grant_premium,
    PAID_SEARCH_STARS,
    PAID_SEARCH_DAYS,
)
```

- [ ] **Step 3: Rewrite `cmd_status`**

Change:

```python
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    status = await get_status(update.effective_user.id)
    text = t(lang, "status_free").format(
        remaining=status["remaining"], limit=FREE_DAILY_LIMIT
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=_main_menu_kb(lang))
```

to:

```python
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    status = await get_status(update.effective_user.id)
    if status["premium"]:
        text = t(lang, "status_premium").format(until=status["premium_until"])
    elif status["remaining"] > 0:
        text = t(lang, "status_free_available")
    else:
        text = t(lang, "status_free_used").format(stars=PAID_SEARCH_STARS)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=_main_menu_kb(lang))
```

(This also fixes a pre-existing, unrelated bug where `cmd_status` never showed `status_premium` at all — it always rendered the free-plan template even for premium users. Since this function is being rewritten anyway, the premium branch is added correctly.)

- [ ] **Step 4: Update the quota-exceeded branch in `handle_city`**

Change:

```python
        await update.message.reply_text(
            t(lang, "rate_limit").format(limit=FREE_DAILY_LIMIT, stars=PAID_SEARCH_STARS),
            parse_mode="HTML",
            reply_markup=_paywall_kb(lang),
        )
```

to:

```python
        await update.message.reply_text(
            t(lang, "rate_limit").format(stars=PAID_SEARCH_STARS),
            parse_mode="HTML",
            reply_markup=_paywall_kb(lang),
        )
```

- [ ] **Step 5: Update the hint in `_run_search`**

Change:

```python
    # Hint about remaining searches when running low (free users only)
    if 0 < remaining <= 2:
        text += t(lang, "searches_left").format(remaining=remaining)
```

to:

```python
    # Tell the user their one lifetime free search is now used up
    if remaining == 0:
        text += t(lang, "free_trial_used").format(stars=PAID_SEARCH_STARS)
```

- [ ] **Step 6: Write the failing tests**

Append to `tests/test_main.py`:

```python
async def test_cmd_status_shows_premium_message(monkeypatch):
    monkeypatch.setattr(
        main, "get_status",
        AsyncMock(return_value={"premium": True, "premium_until": "2026-08-01", "remaining": -1}),
    )
    update = _make_update("/status")
    context = _make_context()

    await main.cmd_status(update, context)

    update.message.reply_text.assert_awaited_once()
    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "status_premium").format(until="2026-08-01")


async def test_cmd_status_shows_free_available(monkeypatch):
    monkeypatch.setattr(
        main, "get_status",
        AsyncMock(return_value={"premium": False, "premium_until": None, "remaining": 1}),
    )
    update = _make_update("/status")
    context = _make_context()

    await main.cmd_status(update, context)

    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "status_free_available")


async def test_cmd_status_shows_free_used(monkeypatch):
    monkeypatch.setattr(
        main, "get_status",
        AsyncMock(return_value={"premium": False, "premium_until": None, "remaining": 0}),
    )
    update = _make_update("/status")
    context = _make_context()

    await main.cmd_status(update, context)

    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "status_free_used").format(stars=main.PAID_SEARCH_STARS)


async def test_run_search_appends_free_trial_notice_when_remaining_zero(monkeypatch):
    fake_result = MagicMock(city_found=True, city="Berlin", events=[], sources_checked=[])
    monkeypatch.setattr(main, "run_milonga_agent", AsyncMock(return_value=fake_result))
    monkeypatch.setattr(main, "_get_redis", lambda: None)

    status_message = MagicMock()
    status_message.delete = AsyncMock()
    update = _make_update("Berlin")
    update.message.reply_text = AsyncMock(return_value=status_message)
    context = _make_context()

    await main._run_search(update, context, "en", "Berlin", 0)

    final_text = update.message.reply_text.call_args_list[-1].args[0]
    assert main.t("en", "free_trial_used").format(stars=main.PAID_SEARCH_STARS) in final_text


async def test_run_search_omits_free_trial_notice_when_premium(monkeypatch):
    fake_result = MagicMock(city_found=True, city="Berlin", events=[], sources_checked=[])
    monkeypatch.setattr(main, "run_milonga_agent", AsyncMock(return_value=fake_result))
    monkeypatch.setattr(main, "_get_redis", lambda: None)

    status_message = MagicMock()
    status_message.delete = AsyncMock()
    update = _make_update("Berlin")
    update.message.reply_text = AsyncMock(return_value=status_message)
    context = _make_context()

    await main._run_search(update, context, "en", "Berlin", -1)

    final_text = update.message.reply_text.call_args_list[-1].args[0]
    assert main.t("en", "free_trial_used").format(stars=main.PAID_SEARCH_STARS) not in final_text
```

- [ ] **Step 7: Run tests to verify they fail, then pass**

Run: `python -m pytest tests/test_main.py -v`
Expected before Steps 1-5: FAIL (`status_free_available`/`status_free_used`/`free_trial_used` keys don't exist yet, `cmd_status` doesn't branch on premium, `_run_search`'s hint condition is still the old one).
Expected after Steps 1-5: all tests in `tests/test_main.py` PASS (11 total: 6 pre-existing + 5 new).

- [ ] **Step 8: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests PASS (9 in test_limits.py + 13 in test_main.py + 33-9-8=... — just confirm the full count is pre-existing-33 minus nothing removed plus 6 (Task 1) plus 5 (Task 2) = 44 total, all green). Note: `tests/test_messages.py` still has its old assertions about `rate_limit` containing `{stars}` (still true) — nothing in that file breaks yet; Task 3 finishes the message cleanup.

- [ ] **Step 9: Commit**

```bash
git add bot/main.py bot/messages.py tests/test_main.py
git commit -m "feat: switch status/paywall messaging to lifetime free-search model"
```

---

### Task 3: Finish localization (ru/he/es) and remove dead message keys

**Files:**
- Modify: `bot/messages.py` (ru/he/es: new `status_free_available`/`status_free_used`/`free_trial_used`, remove old `status_free`/`searches_left`)
- Test: Modify `tests/test_messages.py` (append; existing tests stay — `paywall_*` key tests and `rate_limit` `{stars}` check remain valid unchanged)

**Interfaces:**
- No new functions — string data only, mirroring Task 2's English additions into the other 3 language dicts.

**Note:** `rate_limit` in `ru`/`he`/`es` was already reworded (dropped `{limit}`, matches the wording below) by a Task 2 review fix — a Critical bug was found where the paywall call site stopped passing `limit=...` but those 3 languages' `rate_limit` still required `{limit}`, causing a `KeyError` (silently no response to the user) for every non-English user who exhausted their free search. That fix already landed on `main`/this branch before this task starts. **Do not** look for the old `{limit}`-based `rate_limit` text in `ru`/`he`/`es` — it is already gone. Just skip straight to the `status_*`/`free_trial_used` changes below; if you want to confirm, `MSG["ru"]["rate_limit"]` should already read exactly:

```python
        "rate_limit": (
            "⏳ Ваш единственный бесплатный поиск уже использован.\n\n"
            "Откройте безлимит на 24 часа за {stars} ⭐."
        ),
```

The equivalent already-applied `rate_limit` text exists for `he` and `es` too (same wording pattern, translated) — Steps 2-3 below only show the `status_*` replacement blocks now, since the `rate_limit` part is already done for all three languages.

- [ ] **Step 1: Update `MSG["ru"]`**

Replace:

```python
        "status_premium": "⭐ <b>Статус:</b> Премиум до <b>{until}</b>. Безлимитный поиск.",
        "status_free": "🔍 <b>Статус:</b> Бесплатный план — осталось <b>{remaining}</b> из {limit} поисков сегодня.",
        "searches_left": "\n<i>(осталось {remaining} поиск(а) сегодня)</i>",
```

with:

```python
        "status_premium": "⭐ <b>Статус:</b> Премиум до <b>{until}</b>. Безлимитный поиск.",
        "status_free_available": "🔍 <b>Статус:</b> У вас есть один бесплатный пробный поиск.",
        "status_free_used": "🔍 <b>Статус:</b> Бесплатный поиск уже использован. Доступ на сутки — {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ Это был ваш единственный бесплатный поиск. В следующий раз — {stars} ⭐ за сутки безлимита.</i>",
```

- [ ] **Step 2: Update `MSG["he"]`**

Replace:

```python
        "status_premium": "⭐ <b>סטטוס:</b> פרימיום עד <b>{until}</b>. חיפוש ללא הגבלה.",
        "status_free": "🔍 <b>סטטוס:</b> תוכנית חינמית — נותרו <b>{remaining}</b> מתוך {limit} חיפושים היום.",
        "searches_left": "\n<i>(נותרו {remaining} חיפוש/ים היום)</i>",
```

with:

```python
        "status_premium": "⭐ <b>סטטוס:</b> פרימיום עד <b>{until}</b>. חיפוש ללא הגבלה.",
        "status_free_available": "🔍 <b>סטטוס:</b> יש לך חיפוש ניסיון חינמי אחד זמין.",
        "status_free_used": "🔍 <b>סטטוס:</b> חיפוש הניסיון החינמי כבר נוצל. פתח גישה ללא הגבלה ל-24 שעות תמורת {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ זה היה חיפוש הניסיון החינמי היחיד שלך. בפעם הבאה — {stars} ⭐ לגישה ללא הגבלה ל-24 שעות.</i>",
```

- [ ] **Step 3: Update `MSG["es"]`**

Replace:

```python
        "status_premium": "⭐ <b>Estado:</b> Premium hasta <b>{until}</b>. Búsquedas ilimitadas.",
        "status_free": "🔍 <b>Estado:</b> Plan gratuito — quedan <b>{remaining}</b> de {limit} búsquedas hoy.",
        "searches_left": "\n<i>(quedan {remaining} búsqueda(s) hoy)</i>",
```

with:

```python
        "status_premium": "⭐ <b>Estado:</b> Premium hasta <b>{until}</b>. Búsquedas ilimitadas.",
        "status_free_available": "🔍 <b>Estado:</b> Tienes tu búsqueda de prueba gratuita disponible.",
        "status_free_used": "🔍 <b>Estado:</b> Ya usaste tu búsqueda de prueba gratuita. Desbloquea 24h ilimitadas por {stars} ⭐.",
        "free_trial_used": "\n\n<i>✅ Esa fue tu única búsqueda de prueba gratuita. La próxima vez, desbloquea 24h ilimitadas por {stars} ⭐.</i>",
```

- [ ] **Step 4: Write the failing tests**

Append to `tests/test_messages.py`:

```python
NEW_LIFETIME_KEYS = ["status_free_available", "status_free_used", "free_trial_used"]
REMOVED_KEYS = ["status_free", "searches_left"]


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
@pytest.mark.parametrize("key", NEW_LIFETIME_KEYS)
def test_lifetime_limit_key_present_and_non_empty(lang, key):
    assert MSG[lang].get(key), f"MSG['{lang}']['{key}'] is missing or empty"


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
@pytest.mark.parametrize("key", REMOVED_KEYS)
def test_dead_daily_limit_key_removed(lang, key):
    assert key not in MSG[lang], f"MSG['{lang}']['{key}'] should have been removed"


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
def test_rate_limit_has_no_limit_placeholder(lang):
    assert "{limit}" not in MSG[lang]["rate_limit"]
```

- [ ] **Step 5: Run test to verify it fails**

Run: `python -m pytest tests/test_messages.py -v`
Expected: FAIL on `ru`/`he`/`es` for the new-key checks (not yet added in those languages) and the removed-key checks (still present) before Steps 1-3 are applied.

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_messages.py -v`
Expected: all tests PASS.

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests across `tests/test_limits.py`, `tests/test_main.py`, `tests/test_messages.py` PASS.

- [ ] **Step 8: Commit**

```bash
git add bot/messages.py tests/test_messages.py
git commit -m "feat: localize lifetime free-search messaging for ru/he/es and drop dead keys"
```

---

### Task 4: Manual verification (real Redis, real user-facing behavior)

This task has no code changes — it's a pre-deploy checklist. The gating logic now depends on the real Upstash Redis `stats:known_users` set behaving as expected in production, which unit tests (using an in-memory `FakeRedis`) cannot fully substitute for — and this change affects every user's access on deploy, not just a new feature path.

- [ ] **Step 1: Deploy to a test bot or a low-traffic window**

- [ ] **Step 2: Verify a brand-new Telegram account gets exactly one free search**

Search a city → should succeed and show the city's results plus the new "that was your one free trial search" notice. Immediately search a second (different) city → should show the paywall (only the "Unlock 24h — 150 ⭐" button, no donate button, matching the existing paywall UI from the prior feature).

- [ ] **Step 3: Verify an existing account (one that has searched before this deploy) is immediately gated**

From an account that used the bot before this change shipped, send any city → should go straight to the paywall without a free search, since that account is already in `stats:known_users`.

- [ ] **Step 4: Verify `/status` reflects all three states**

Before any search (new account): `/status` → "you have your one free trial search available". After the one free search: `/status` → "free trial search already used... 150 ⭐". After buying the 24h pass: `/status` → the premium message with the correct expiry date (this also confirms the `cmd_status` premium-branch fix from Task 2).

- [ ] **Step 5: Verify the paid pass still works but does NOT restore future free searches**

Buy the 24h pass, confirm unlimited search works during the 24h window (as before), then confirm (or reason from the code, since waiting 24h in test isn't practical) that after `premium_until` passes, `check_and_increment` falls through to the `stats:known_users` check and returns `(False, 0)` again — not a fresh free search.

- [ ] **Step 6: Confirm `/stats` (admin) "active today" still increments sensibly**

Have 2-3 different test accounts each send one message on the same day; confirm the admin `/stats` "Active today" count reflects unique users for that day (via the new `stats:active_users:{date}` set), not merged with "new users" or "known users" totals.
