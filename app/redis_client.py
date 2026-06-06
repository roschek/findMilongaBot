import os
from datetime import datetime, timedelta, timezone

_instance = None


def get_redis():
    global _instance
    if _instance is None:
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if url and token:
            from upstash_redis.asyncio import Redis
            _instance = Redis(url=url, token=token)
    return _instance


def _ttl_until_midnight() -> int:
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(300, int((midnight - now).total_seconds()))
