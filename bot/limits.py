import json
import os
from datetime import date, timedelta
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "users_db.json"
FREE_DAILY_LIMIT = 20
PREMIUM_DAYS = 30
_REDIS_KEY = "users_db"


def _redis():
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        from upstash_redis import Redis
        return Redis(url=url, token=token)
    return None


def _load() -> dict:
    r = _redis()
    if r:
        val = r.get(_REDIS_KEY)
        return json.loads(val) if val else {}
    if _DB_PATH.exists():
        try:
            return json.loads(_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    r = _redis()
    if r:
        r.set(_REDIS_KEY, json.dumps(data, ensure_ascii=False))
    else:
        _DB_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _entry(data: dict, user_id: int) -> dict:
    key = str(user_id)
    if key not in data:
        data[key] = {}
    return data[key]


def check_and_increment(user_id: int) -> tuple[bool, int]:
    """
    Returns (allowed, remaining).
    remaining = -1 means premium (unlimited).
    Increments counter if allowed.
    """
    data = _load()
    entry = _entry(data, user_id)
    today = str(date.today())

    premium_until = entry.get("premium_until")
    if premium_until and premium_until >= today:
        return True, -1  # no save needed — nothing changed

    if entry.get("date") != today:
        entry["date"] = today
        entry["count"] = 0

    count = entry.get("count", 0)
    if count >= FREE_DAILY_LIMIT:
        _save(data)
        return False, 0

    entry["count"] = count + 1
    _save(data)
    return True, FREE_DAILY_LIMIT - count - 1


def get_status(user_id: int) -> dict:
    """Returns {"premium": bool, "premium_until": str|None, "remaining": int|-1}."""
    data = _load()
    entry = data.get(str(user_id), {})
    today = str(date.today())
    premium_until = entry.get("premium_until")
    is_premium = bool(premium_until and premium_until >= today)
    if is_premium:
        remaining = -1
    else:
        used = entry.get("count", 0) if entry.get("date") == today else 0
        remaining = max(0, FREE_DAILY_LIMIT - used)
    return {"premium": is_premium, "premium_until": premium_until, "remaining": remaining}


def get_search_stats() -> dict:
    """Returns basic usage stats for the admin command."""
    data = _load()
    today = str(date.today())
    total_users = len(data)
    active_today = sum(1 for u in data.values() if u.get("date") == today)
    searches_today = sum(u.get("count", 0) for u in data.values() if u.get("date") == today)
    return {"total_users": total_users, "active_today": active_today, "searches_today": searches_today}


def grant_premium(user_id: int, days: int = PREMIUM_DAYS) -> str:
    """Grant premium for `days`. Stacks on top of existing premium. Returns expiry date string."""
    data = _load()
    entry = _entry(data, user_id)
    today = date.today()

    current = entry.get("premium_until")
    start = date.fromisoformat(current) if (current and current >= str(today)) else today
    expiry = start + timedelta(days=days)
    entry["premium_until"] = str(expiry)
    _save(data)
    return str(expiry)
