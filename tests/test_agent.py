from unittest.mock import AsyncMock, MagicMock

from app import agent
from app.models import MilongaEvent


def _fake_event(name: str = "Test Milonga") -> MilongaEvent:
    return MilongaEvent(
        name=name,
        source_url="https://www.gotango.today/en/event/fake",
        confidence="high",
        date="2026-07-18",
    )


async def test_run_milonga_agent_uses_gotango_events_when_covered(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(agent.genai, "Client", MagicMock())
    monkeypatch.setattr(agent, "_normalize_city", AsyncMock(return_value=("Buenos Aires", True)))
    monkeypatch.setattr(agent, "_get_redis", lambda: None)
    fake_events = [_fake_event()]
    monkeypatch.setattr(agent, "fetch_gotango_events", AsyncMock(return_value=fake_events))
    known_sites_mock = AsyncMock()
    monkeypatch.setattr(agent.site_db, "get_schedule_sites", known_sites_mock)

    result = await agent.run_milonga_agent(city="Buenos Aires", date="2026-07-18", days_ahead=1)

    assert result.events == fake_events
    assert result.city_found is True
    assert result.city == "Buenos Aires"
    assert result.sources_checked == ["https://www.gotango.today/en/buenos-aires"]
    known_sites_mock.assert_not_awaited()


async def test_run_milonga_agent_falls_back_when_not_covered(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(agent.genai, "Client", MagicMock())
    monkeypatch.setattr(agent, "_normalize_city", AsyncMock(return_value=("Moscow", True)))
    monkeypatch.setattr(agent, "_get_redis", lambda: None)
    monkeypatch.setattr(agent, "fetch_gotango_events", AsyncMock(return_value=None))
    known_sites_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(agent.site_db, "get_schedule_sites", known_sites_mock)
    monkeypatch.setattr(agent.site_db, "get_ics_feeds", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent, "_search_phase", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        agent, "_run_with_urls", AsyncMock(return_value=([], [], [], [], [], []))
    )

    await agent.run_milonga_agent(city="Moscow", date="2026-07-18", days_ahead=1)

    known_sites_mock.assert_awaited_once()
