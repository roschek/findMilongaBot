from unittest.mock import AsyncMock, MagicMock

import bot.main as main


def _make_update(text: str, user_id: int = 1, lang: str = "en"):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_user = MagicMock(id=user_id, language_code=lang)
    return update


def _make_context():
    context = MagicMock()
    context.user_data = {}
    return context


async def test_handle_city_delegates_to_run_search_with_remaining(monkeypatch):
    monkeypatch.setattr(main, "check_and_increment", AsyncMock(return_value=(True, 3)))
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_update("Berlin")
    context = _make_context()

    await main.handle_city(update, context)

    run_search_mock.assert_awaited_once_with(update, context, "en", "Berlin", 3)


async def test_handle_city_quota_exceeded_saves_pending_city_and_shows_paywall(monkeypatch):
    monkeypatch.setattr(main, "check_and_increment", AsyncMock(return_value=(False, 0)))

    update = _make_update("Berlin")
    context = _make_context()

    await main.handle_city(update, context)

    assert context.user_data["pending_city"] == "Berlin"
    update.message.reply_text.assert_awaited_once()
    _, kwargs = update.message.reply_text.call_args
    kb = kwargs["reply_markup"]
    assert kb.inline_keyboard[0][0].callback_data == "buy_search_pass"


async def test_cb_buy_search_pass_sends_invoice_with_fixed_price():
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.reply_invoice = AsyncMock()
    update.effective_user = MagicMock(language_code="en")
    context = _make_context()

    await main.cb_buy_search_pass(update, context)

    update.callback_query.message.reply_invoice.assert_awaited_once()
    _, kwargs = update.callback_query.message.reply_invoice.call_args
    assert kwargs["payload"] == "searchpass"
    assert kwargs["currency"] == "XTR"
    assert kwargs["prices"][0].amount == main.PAID_SEARCH_STARS
