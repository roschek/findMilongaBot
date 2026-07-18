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
