import json
from datetime import date, timedelta
from pathlib import Path

from app.redis_client import get_redis as _redis, _ttl_until_midnight

_DB_PATH = Path(__file__).parent.parent / "users_db.json"
FREE_DAILY_LIMIT = 5
PREMIUM_DAYS = 30
_REDIS_KEY = "users_db"


async def _load() -> dict:
    r = _redis()
    if r:
        try:
            val = await r.get(_REDIS_KEY)
            return json.loads(val) if val else {}
        except Exception:
            pass
    if _DB_PATH.exists():
        try:
            return json.loads(_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


async def _save(data: dict) -> None:
    r = _redis()
    if r:
        try:
            await r.set(_REDIS_KEY, json.dumps(data, ensure_ascii=False))
            return
        except Exception:
            pass
    _DB_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _entry(data: dict, user_id: int) -> dict:
    key = str(user_id)
    if key not in data:
        data[key] = {}
    return data[key]


async def check_and_increment(user_id: int) -> tuple[bool, int]:
    """
    Returns (allowed, remaining).
    remaining = -1 means premium (unlimited).
    Increments counter if allowed.
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

            # Atomic rate-limit increment
            rl_key = f"rl:{user_id}:{today}"
            count = await r.incr(rl_key)
            if count == 1:
                await r.expire(rl_key, _ttl_until_midnight())
            if count > FREE_DAILY_LIMIT:
                return False, 0
        except Exception:
            pass
        else:
            # Non-critical stats — isolated so failures never affect rate-limit result
            try:
                day_key = f"stats:day:{today}"
                await r.hincrby(day_key, "searches", 1)
                await r.hincrby("stats:totals", "searches", 1)
                if count == 1:
                    await r.hincrby(day_key, "active", 1)
                    # Keep day key for ~2 days so yesterday's stats survive past midnight
                    await r.expire(day_key, _ttl_until_midnight() + 86400)
                added = await r.sadd("stats:known_users", str(user_id))
                if added == 1:
                    await r.hincrby(day_key, "new_users", 1)
            except Exception:
                pass
            return True, FREE_DAILY_LIMIT - count

    # File fallback (local dev — sequential PTB updates, no race condition in practice)
    data = await _load()
    entry = _entry(data, user_id)

    premium_until = entry.get("premium_until")
    if premium_until and premium_until >= today:
        return True, -1

    if entry.get("date") != today:
        entry["date"] = today
        entry["count"] = 0

    count = entry.get("count", 0)
    if count >= FREE_DAILY_LIMIT:
        return False, 0

    entry["count"] = count + 1
    await _save(data)
    return True, FREE_DAILY_LIMIT - count - 1


async def get_status(user_id: int) -> dict:
    """Returns {"premium": bool, "premium_until": str|None, "remaining": int|-1}."""
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
            val = await r.get(f"rl:{user_id}:{today}")
            used = int(val) if val else 0
            return {"premium": False, "premium_until": None, "remaining": max(0, FREE_DAILY_LIMIT - used)}
        except Exception:
            pass
    used = entry.get("count", 0) if entry.get("date") == today else 0
    return {"premium": False, "premium_until": premium_until, "remaining": max(0, FREE_DAILY_LIMIT - used)}


async def get_search_stats() -> dict:
    """Returns extended usage stats for the admin command."""
    data = await _load()
    today = str(date.today())
    total_users = len(data)
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
    r = _redis()
    if not r:
        return base
    try:
        def _i(d: dict, key: str) -> int:
            return int(d.get(key) or 0)

        day_raw = await r.hgetall(f"stats:day:{today}") or {}
        totals_raw = await r.hgetall("stats:totals") or {}
        cities_raw = await r.zrevrange("stats:cities", 0, 14, withscores=True) or []
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
    except Exception:
        return base


async def grant_premium(user_id: int, days: int = PREMIUM_DAYS) -> str:
    """Grant premium for `days`. Stacks on top of existing premium. Returns expiry date string."""
    data = await _load()
    entry = _entry(data, user_id)
    today = date.today()

    current = entry.get("premium_until")
    start = date.fromisoformat(current) if (current and current >= str(today)) else today
    expiry = start + timedelta(days=days)
    entry["premium_until"] = str(expiry)
    await _save(data)
    return str(expiry)
