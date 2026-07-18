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
    monkeypatch.setattr(main, "check_and_increment", AsyncMock(return_value=(True, 0)))
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_update("Berlin")
    context = _make_context()

    await main.handle_city(update, context)

    run_search_mock.assert_awaited_once_with(update, context, "en", "Berlin", 0)


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


def _make_payment_update(payload: str, stars: int, user_id: int = 1, lang: str = "en"):
    update = MagicMock()
    update.effective_user = MagicMock(id=user_id, language_code=lang)
    update.message.successful_payment.invoice_payload = payload
    update.message.successful_payment.total_amount = stars
    update.message.reply_text = AsyncMock()
    return update


async def test_successful_payment_searchpass_continues_pending_search(monkeypatch):
    monkeypatch.setattr(main, "grant_premium", AsyncMock(return_value="2026-07-17"))
    monkeypatch.setattr(main, "_get_redis", lambda: None)
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_payment_update("searchpass", main.PAID_SEARCH_STARS)
    context = _make_context()
    context.user_data["pending_city"] = "Berlin"

    await main.successful_payment(update, context)

    main.grant_premium.assert_awaited_once_with(1, days=main.PAID_SEARCH_DAYS)
    run_search_mock.assert_awaited_once_with(update, context, "en", "Berlin", -1)
    assert "pending_city" not in context.user_data


async def test_successful_payment_searchpass_without_pending_city_shows_unlocked(monkeypatch):
    monkeypatch.setattr(main, "grant_premium", AsyncMock(return_value="2026-07-17"))
    monkeypatch.setattr(main, "_get_redis", lambda: None)
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_payment_update("searchpass", main.PAID_SEARCH_STARS)
    context = _make_context()

    await main.successful_payment(update, context)

    run_search_mock.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "paywall_unlocked")


async def test_successful_payment_donate_payload_keeps_existing_behavior(monkeypatch):
    grant_premium_mock = AsyncMock()
    monkeypatch.setattr(main, "grant_premium", grant_premium_mock)
    monkeypatch.setattr(main, "_get_redis", lambda: None)
    run_search_mock = AsyncMock()
    monkeypatch.setattr(main, "_run_search", run_search_mock)

    update = _make_payment_update("donate_250", 250)
    context = _make_context()

    await main.successful_payment(update, context)

    grant_premium_mock.assert_not_awaited()
    run_search_mock.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert args[0] == main.t("en", "donate_thanks")
    assert kwargs["reply_markup"] is not None


async def test_cmd_status_shows_premium_message(monkeypatch):
    monkeypatch.setattr(
        main, "get_status",
        AsyncMock(return_value={"premium": True, "premium_until": "2026-08-01", "remaining": -1}),
    )
    update = _make_update("/status")
    context = _make_context()

    await main.cmd_status(update, context)

    update.message.reply_text.assert_awaited_once()
    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "status_premium").format(until="2026-08-01")


async def test_cmd_status_shows_free_available(monkeypatch):
    monkeypatch.setattr(
        main, "get_status",
        AsyncMock(return_value={"premium": False, "premium_until": None, "remaining": 1}),
    )
    update = _make_update("/status")
    context = _make_context()

    await main.cmd_status(update, context)

    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "status_free_available")


async def test_cmd_status_shows_free_used(monkeypatch):
    monkeypatch.setattr(
        main, "get_status",
        AsyncMock(return_value={"premium": False, "premium_until": None, "remaining": 0}),
    )
    update = _make_update("/status")
    context = _make_context()

    await main.cmd_status(update, context)

    args, _ = update.message.reply_text.call_args
    assert args[0] == main.t("en", "status_free_used").format(stars=main.PAID_SEARCH_STARS)


async def test_run_search_appends_free_trial_notice_when_remaining_zero(monkeypatch):
    fake_result = MagicMock(city_found=True, city="Berlin", events=[], sources_checked=[])
    monkeypatch.setattr(main, "run_milonga_agent", AsyncMock(return_value=fake_result))
    monkeypatch.setattr(main, "_get_redis", lambda: None)

    status_message = MagicMock()
    status_message.delete = AsyncMock()
    update = _make_update("Berlin")
    update.message.reply_text = AsyncMock(return_value=status_message)
    context = _make_context()

    await main._run_search(update, context, "en", "Berlin", 0)

    final_text = update.message.reply_text.call_args_list[-1].args[0]
    assert main.t("en", "free_trial_used").format(stars=main.PAID_SEARCH_STARS) in final_text


async def test_run_search_omits_free_trial_notice_when_premium(monkeypatch):
    fake_result = MagicMock(city_found=True, city="Berlin", events=[], sources_checked=[])
    monkeypatch.setattr(main, "run_milonga_agent", AsyncMock(return_value=fake_result))
    monkeypatch.setattr(main, "_get_redis", lambda: None)

    status_message = MagicMock()
    status_message.delete = AsyncMock()
    update = _make_update("Berlin")
    update.message.reply_text = AsyncMock(return_value=status_message)
    context = _make_context()

    await main._run_search(update, context, "en", "Berlin", -1)

    final_text = update.message.reply_text.call_args_list[-1].args[0]
    assert main.t("en", "free_trial_used").format(stars=main.PAID_SEARCH_STARS) not in final_text
