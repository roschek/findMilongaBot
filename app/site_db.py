import json
from datetime import date
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "sites_db.json"
_DISCOVERY_TTL_DAYS = 30
_MAX_FAILURES = 3


def _load() -> dict:
    if _DB_PATH.exists():
        try:
            return json.loads(_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    _DB_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _entry_valid(entry: dict) -> bool:
    discovered = date.fromisoformat(entry["discovered_at"])
    return (date.today() - discovered).days <= _DISCOVERY_TTL_DAYS


def _active_urls(entries: list[dict]) -> list[str]:
    return [s["url"] for s in entries if s.get("failures", 0) < _MAX_FAILURES]


def get_schedule_sites(city: str) -> list[str] | None:
    """
    Return URLs of sites known to carry schedule data, or None if not cached / TTL expired.
    These are sites that previously yielded at least one event.
    """
    data = _load()
    entry = data.get(city.lower())
    if not entry or not _entry_valid(entry):
        return None
    urls = _active_urls(entry.get("schedule_sites", []))
    ics = _active_urls(entry.get("ics_feeds", []))
    return (urls + ics) if (urls or ics) else None


def get_ics_feeds(city: str) -> list[str]:
    data = _load()
    entry = data.get(city.lower())
    if not entry or not _entry_valid(entry):
        return []
    return _active_urls(entry.get("ics_feeds", []))


def save_productive_sites(city: str, web_urls: list[str], ics_urls: list[str]) -> None:
    """
    Save only sites that actually produced events.
    web_urls: source_url values from extracted events (deduped).
    ics_urls: ICS feed URLs that returned at least one event.
    """
    data = _load()
    key = city.lower()
    entry = data.get(key, {"discovered_at": date.today().isoformat()})

    def _merge(section: str, new_urls: list[str]) -> None:
        if not new_urls:
            return  # never overwrite existing data with an empty list
        existing = {s["url"]: s for s in entry.get(section, [])}
        entry[section] = [
            existing[u] if u in existing else {"url": u, "failures": 0}
            for u in new_urls
        ]

    _merge("schedule_sites", web_urls)
    _merge("ics_feeds", ics_urls)
    entry["discovered_at"] = date.today().isoformat()
    data[key] = entry
    _save(data)


def _mark(city: str, url: str, section: str, failure: bool) -> None:
    data = _load()
    key = city.lower()
    if key not in data:
        return
    for site in data[key].get(section, []):
        if site["url"] == url:
            site["failures"] = (site.get("failures", 0) + 1) if failure else 0
            break
    _save(data)


def mark_failure(city: str, url: str) -> None:
    _mark(city, url, "schedule_sites", failure=True)


def mark_success(city: str, url: str) -> None:
    _mark(city, url, "schedule_sites", failure=False)


def mark_ics_failure(city: str, url: str) -> None:
    _mark(city, url, "ics_feeds", failure=True)


def mark_ics_success(city: str, url: str) -> None:
    _mark(city, url, "ics_feeds", failure=False)
