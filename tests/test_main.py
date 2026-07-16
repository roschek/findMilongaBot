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
