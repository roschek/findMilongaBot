from cachetools import TTLCache

# Cache results for 3 hours — schedules don't change often
_cache: TTLCache = TTLCache(maxsize=100, ttl=3 * 60 * 60)


def get_cached(city: str, date: str):
    return _cache.get(f"{city.lower()}:{date}")


def set_cached(city: str, date: str, value) -> None:
    _cache[f"{city.lower()}:{date}"] = value
