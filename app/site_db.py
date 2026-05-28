import json
import os
from datetime import date
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "sites_db.json"
_DISCOVERY_TTL_DAYS = 30
_MAX_FAILURES = 3
_REDIS_KEY = "sites_db"


def _redis():
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        from upstash_redis.asyncio import Redis
        return Redis(url=url, token=token)
    return None


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


def _entry_valid(entry: dict) -> bool:
    discovered = date.fromisoformat(entry["discovered_at"])
    return (date.today() - discovered).days <= _DISCOVERY_TTL_DAYS


def _active_urls(entries: list[dict]) -> list[str]:
    return [s["url"] for s in entries if s.get("failures", 0) < _MAX_FAILURES]


async def get_schedule_sites(city: str) -> list[str] | None:
    data = await _load()
    entry = data.get(city.lower())
    if not entry or not _entry_valid(entry):
        return None
    urls = _active_urls(entry.get("schedule_sites", []))
    ics = _active_urls(entry.get("ics_feeds", []))
    return (urls + ics) if (urls or ics) else None


async def get_ics_feeds(city: str) -> list[str]:
    data = await _load()
    entry = data.get(city.lower())
    if not entry or not _entry_valid(entry):
        return []
    return _active_urls(entry.get("ics_feeds", []))


async def save_productive_sites(city: str, web_urls: list[str], ics_urls: list[str]) -> None:
    data = await _load()
    key = city.lower()
    entry = data.get(key, {"discovered_at": date.today().isoformat()})

    def _merge(section: str, new_urls: list[str]) -> None:
        if not new_urls:
            return
        existing = {s["url"]: s for s in entry.get(section, [])}
        for u in new_urls:
            if u not in existing:
                existing[u] = {"url": u, "failures": 0}
        entry[section] = list(existing.values())

    _merge("schedule_sites", web_urls)
    _merge("ics_feeds", ics_urls)
    entry["discovered_at"] = date.today().isoformat()
    data[key] = entry
    await _save(data)


async def _mark(city: str, url: str, section: str, failure: bool) -> None:
    data = await _load()
    key = city.lower()
    if key not in data:
        return
    for site in data[key].get(section, []):
        if site["url"] == url:
            site["failures"] = (site.get("failures", 0) + 1) if failure else 0
            break
    await _save(data)


async def mark_failure(city: str, url: str) -> None:
    await _mark(city, url, "schedule_sites", failure=True)


async def mark_success(city: str, url: str) -> None:
    await _mark(city, url, "schedule_sites", failure=False)


async def mark_ics_failure(city: str, url: str) -> None:
    await _mark(city, url, "ics_feeds", failure=True)


async def mark_ics_success(city: str, url: str) -> None:
    await _mark(city, url, "ics_feeds", failure=False)
