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
