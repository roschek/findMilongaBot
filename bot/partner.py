import json
import logging
import os

import httpx

from app.redis_client import get_redis as _get_redis

PARTNER_TTL = 20 * 3600  # 20 hours

# Sentinel: distinguishes "not yet tried" from "tried and failed" (None).
# Without it, every call retries os.environ lookup when GEMINI_API_KEY is absent.
_UNSET = object()
_genai_client = _UNSET


def _get_genai_client():
    global _genai_client
    if _genai_client is _UNSET:
        try:
            from google import genai
            _genai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        except Exception:
            logging.warning("genai client unavailable — city normalization disabled")
            _genai_client = None
    return _genai_client


def city_key(city: str) -> str:
    return city.lower().strip()


async def save_partner(
    user_id: int,
    city: str,
    role: str,
    note: str,
    username: str | None,
    lang: str = "en",
) -> None:
    r = _get_redis()
    if not r:
        return
    key = city_key(city)
    data = json.dumps(
        {"city": city, "city_key": key, "role": role, "note": note, "username": username, "lang": lang},
        ensure_ascii=False,
    )
    await r.set(f"partner:{user_id}", data, ex=PARTNER_TTL)
    await r.sadd(f"partners_city:{key}", str(user_id))
    await r.expire(f"partners_city:{key}", PARTNER_TTL)


async def get_partner(user_id: int) -> dict | None:
    r = _get_redis()
    if not r:
        return None
    raw = await r.get(f"partner:{user_id}")
    return json.loads(raw) if raw else None


async def get_partners(city: str, exclude_user_id: int | None = None) -> list[dict]:
    r = _get_redis()
    if not r:
        return []
    key = city_key(city)
    user_ids = await r.smembers(f"partners_city:{key}")
    if not user_ids:
        return []
    filtered = [uid for uid in user_ids if not (exclude_user_id and int(uid) == exclude_user_id)]
    if not filtered:
        return []
    raws = await r.mget(*[f"partner:{uid}" for uid in filtered])
    partners = []
    stale = []
    for uid, raw in zip(filtered, raws):
        if raw:
            partners.append({"user_id": int(uid), **json.loads(raw)})
        else:
            stale.append(uid)
    for uid in stale:
        await r.srem(f"partners_city:{key}", uid)
    return partners


async def get_partners_by_ids(user_ids: list[int]) -> dict[int, dict]:
    """Batch-fetch partner records by user ID. Returns {user_id: data} for live records only."""
    r = _get_redis()
    if not r or not user_ids:
        return {}
    raws = await r.mget(*[f"partner:{uid}" for uid in user_ids])
    return {uid: json.loads(raw) for uid, raw in zip(user_ids, raws) if raw}


async def remove_partner(user_id: int) -> str | None:
    """Returns city of removed request, or None if not found."""
    r = _get_redis()
    if not r:
        return None
    raw = await r.get(f"partner:{user_id}")
    if not raw:
        return None
    data = json.loads(raw)
    key = data.get("city_key", "")
    await r.srem(f"partners_city:{key}", str(user_id))
    await r.delete(f"partner:{user_id}")
    return data.get("city")


async def add_notify(user_id: int, city: str) -> None:
    """Register user to be notified when someone posts in their city."""
    r = _get_redis()
    if not r:
        return
    key = city_key(city)
    await r.sadd(f"partner_notify:{key}", str(user_id))
    await r.expire(f"partner_notify:{key}", PARTNER_TTL)


async def pop_notify_users(city: str, exclude_user_id: int) -> list[int]:
    """Atomically return and clear user_ids waiting for notification in this city."""
    r = _get_redis()
    if not r:
        return []
    notify_key = f"partner_notify:{city_key(city)}"
    # Pipeline ensures SMEMBERS+DEL are atomic (single HTTP request to upstash).
    # Prevents two concurrent callers from both reading the same set and sending
    # duplicate notifications.
    pipe = r.pipeline()
    pipe.smembers(notify_key)
    pipe.delete(notify_key)
    try:
        results = await pipe.execute()
    except Exception:
        logging.warning("pop_notify_users pipeline failed for city %r", city)
        return []
    user_ids = results[0] or set()
    return [int(uid) for uid in user_ids if int(uid) != exclude_user_id]


async def normalize_partner_city(city: str) -> str | None:
    """Canonicalize a city name via Gemini. Returns None on failure or unavailable client."""
    client = _get_genai_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=(
                f"What is the canonical English name of the city or town '{city}'?\n"
                f"If it is a real place but small (under 300k population or unlikely to have an active tango scene), "
                f"return the nearest large city instead (e.g. 'Petah Tikva' → 'Tel Aviv', 'Mytishchi' → 'Moscow').\n"
                f"If it is a real major city, reply with just the canonical English name (e.g. 'Moscow', 'Tel Aviv', 'Tbilisi').\n"
                f"If it is NOT a real place name at all, reply with exactly: UNKNOWN\n"
                f"Reply with just the city name, nothing else."
            ),
            config=types.GenerateContentConfig(temperature=0),
        )
        result = response.candidates[0].content.parts[0].text.strip().strip(".")
        if not result or result.upper() == "UNKNOWN":
            return None
        return result
    except Exception:
        logging.warning("normalize_partner_city failed for %r", city)
        return None


async def reverse_geocode(lat: float, lon: float) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": "MilongaFinderBot/1.0"},
            )
            addr = resp.json().get("address", {})
            return (
                addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or addr.get("county")
            )
    except Exception:
        logging.warning("reverse_geocode failed lat=%s lon=%s", lat, lon)
        return None
