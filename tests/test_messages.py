import pytest

from bot.messages import MSG

NEW_KEYS = [
    "paywall_button",
    "paywall_invoice_title",
    "paywall_invoice_desc",
    "paywall_thanks",
    "paywall_unlocked",
]


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
@pytest.mark.parametrize("key", NEW_KEYS)
def test_paywall_key_present_and_non_empty(lang, key):
    assert MSG[lang].get(key), f"MSG['{lang}']['{key}'] is missing or empty"


@pytest.mark.parametrize("lang", ["en", "ru", "he", "es"])
def test_rate_limit_mentions_price_placeholder(lang):
    assert "{stars}" in MSG[lang]["rate_limit"]


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
