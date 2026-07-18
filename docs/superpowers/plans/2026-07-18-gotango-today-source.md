# gotango.today as Primary Data Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before falling back to the existing Gemini-based search/extraction pipeline, try gotango.today (a structured tango-event aggregator) as a free, LLM-free data source. For cities it covers, this eliminates the two most expensive Gemini calls (`_search_phase` with Google Search grounding, and `_extract_events`) entirely.

**Architecture:** A new module `app/gotango.py` does a cheap direct HTTP existence check against `gotango.today` (its origin server returns a real HTTP 404 for uncovered cities, confirmed by manual testing), and only if covered, fetches the JS-rendered page via the already-used Jina Reader proxy (`r.jina.ai`) and parses event cards deterministically with BeautifulSoup — no LLM call involved. `app/agent.py`'s `run_milonga_agent` tries this first (after the existing cheap city-normalization step), and only falls through to the existing `known_sites` → search → extract pipeline if gotango.today doesn't cover the city.

**Tech Stack:** httpx (existing dependency), BeautifulSoup (existing dependency), Jina Reader via HTTP (existing pattern, see `app/tools.py:read_website`). No new dependencies.

## Global Constraints

- Only event types `Milonga` and `Practica` are kept (case-insensitive match) — `Workshop`, `Show`, and any other type tag gotango.today uses are filtered out, matching the bot's stated scope (milongas + practicas only).
- Confidence is always `"high"` for gotango.today-sourced events — this is structured organizer data, not LLM inference from unstructured text.
- No negative caching: an uncovered city (404) is not persisted to `site_db` or anywhere else — every request re-checks directly. This is a deliberate simplicity choice (see spec) so a newly-added city on gotango.today is picked up automatically without any cache invalidation.
- `address` and `price` are not available from gotango.today's card view and stay `None` on the resulting `MilongaEvent` — consistent with how other sources already leave these fields unset when unknown.
- Date-to-event mapping is positional: gotango.today's date-range query (`?from=X&to=Y`) returns one date-section (with its own event grid) per requested date, in the same order as requested — confirmed by manual testing (4 requested dates → 4 sections in order). This plan zips `dates` with the parsed date-sections positionally; if gotango.today ever omits a middle date's section (not just trailing ones), later dates would misalign. This is an accepted, documented risk (matches the project's existing tolerance for similar edge cases, e.g. the `sites_db` race condition noted in `NOTES.md`) — not something this plan defends against.
- All CSS selectors/class-name checks below were verified against real, live-fetched HTML from `gotango.today/en/buenos-aires` (July 2026) — see the design spec for the raw research. The test fixture (`tests/fixtures/gotango_buenos_aires.html`) is a trimmed excerpt of real, verified markup (not synthesized), covering: a milonga with a DJ, a milonga without a DJ, a practica, and a workshop (to prove type filtering), across two different dates (to prove positional date mapping).

---

### Task 1: Create `app/gotango.py` — fetch, parse, filter

**Files:**
- Create: `app/gotango.py`
- Create: `tests/fixtures/gotango_buenos_aires.html` (real, trimmed markup — copy verbatim from this plan's Step 1, do not re-fetch or regenerate it)
- Test: Create `tests/test_gotango.py`

**Interfaces:**
- Produces: `async def fetch_gotango_events(city: str, dates: list[str]) -> list[MilongaEvent] | None` — the only function `app/agent.py` (Task 2) calls. Returns `None` if gotango.today doesn't cover `city` (HTTP 404 on direct check); returns a list (possibly empty) of `MilongaEvent` if it does.
- Produces: `def gotango_city_url(city: str) -> str` — the `https://www.gotango.today/en/{slug}` URL for a city, used by Task 2 to populate `MilongaResponse.sources_checked`/`sources_found`.
- Consumes: `app.models.MilongaEvent` (existing, unchanged).

- [ ] **Step 1: Create the test fixture**

Create `tests/fixtures/gotango_buenos_aires.html` with exactly this content (real markup fragments captured from a live fetch of `gotango.today/en/buenos-aires?from=2026-07-18&to=2026-07-21` via Jina Reader in HTML mode, trimmed to 5 representative cards across 2 dates):

```html
<!DOCTYPE html>
<html><body>
<div class="date-section">
<span class="font-bold tabular-nums text-[var(--accent-gold)]">18</span><span class="text-sm text-muted-foreground">Saturday<span class="mx-1 opacity-50">/</span>July</span>
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
<a class="group block overflow-hidden rounded-[10px] border border-border bg-card transition-all duration-200 hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--accent-gold)_28%,hsl(var(--border)))] hover:shadow-lg " href="/en/event/ab5f469a-011c-4667-ad81-5329a3fb8dd7"><div class="relative aspect-[16/9]"><div data-testid="identity-panel" data-role="avatar" class="relative grid aspect-[16/9] place-items-center overflow-hidden"><span class="pointer-events-none absolute left-3 top-2.5 max-w-[75%] truncate font-mono text-[10px] uppercase tracking-[0.14em] text-foreground opacity-50">Gustavo Peris</span></div></div><div class="flex flex-col gap-1.5 p-3"><div class="flex flex-wrap items-baseline gap-2"><span class="font-mono text-[13px] font-semibold tracking-[0.02em] text-foreground">5:00 — 9:00</span><span data-testid="status-chip-scheduled" class="inline-flex items-center gap-1 rounded font-semibold uppercase tracking-wider border border-border bg-muted text-muted-foreground py-0.5 ml-auto shrink-0 text-[0.65rem] px-2"><svg class="lucide lucide-calendar-clock h-2.5 w-2.5 shrink-0"></svg>Regular schedule</span></div><h3 class="line-clamp-2 text-[15px] font-semibold leading-[1.3] tracking-[-0.01em] text-foreground">After House Tango de madrugada</h3><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-map-pin h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">Espacio Almagro</span></div><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-music h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">TDJ: Norma juarez</span></div><div class="mt-0.5 flex flex-wrap gap-1.5"><span class="inline-flex items-center gap-1 rounded-[5px] border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Milonga</span></div></div></a>
<a class="group block overflow-hidden rounded-[10px] border border-border bg-card" href="/en/event/0fd66b7c-8684-498d-a2b8-dbc9df9efcc8"><div class="flex flex-col gap-1.5 p-3"><div class="flex flex-wrap items-baseline gap-2"><span class="font-mono text-[13px] font-semibold tracking-[0.02em] text-foreground">15:00 — 19:00</span><span data-testid="status-chip-scheduled" class="inline-flex items-center gap-1 rounded font-semibold uppercase tracking-wider border border-border bg-muted text-muted-foreground py-0.5 ml-auto shrink-0 text-[0.65rem] px-2"><svg class="lucide lucide-calendar-clock h-2.5 w-2.5 shrink-0"></svg>Regular schedule</span></div><h3 class="line-clamp-2 text-[15px] font-semibold leading-[1.3] tracking-[-0.01em] text-foreground">La Maria Rolera</h3><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-map-pin h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">La Paila</span></div><div class="mt-0.5 flex flex-wrap gap-1.5"><span class="inline-flex items-center gap-1 rounded-[5px] border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Milonga</span></div></div></a>
<a class="group block overflow-hidden rounded-[10px] border border-border bg-card" href="/en/event/b7e7f45d-b8eb-4831-b5e6-a24e6df839cf"><div class="flex flex-col gap-1.5 p-3"><div class="flex flex-wrap items-baseline gap-2"><span class="font-mono text-[13px] font-semibold tracking-[0.02em] text-foreground">18:00 — 21:00</span><span data-testid="status-chip-scheduled" class="inline-flex items-center gap-1 rounded font-semibold uppercase tracking-wider border border-border bg-muted text-muted-foreground py-0.5 ml-auto shrink-0 text-[0.65rem] px-2"><svg class="lucide lucide-calendar-clock h-2.5 w-2.5 shrink-0"></svg>Regular schedule</span></div><h3 class="line-clamp-2 text-[15px] font-semibold leading-[1.3] tracking-[-0.01em] text-foreground">PractiCuir</h3><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-map-pin h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">Estudio Tango Cuir</span></div><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-music h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">TDJ: Anahí Carballo</span></div><div class="mt-0.5 flex flex-wrap gap-1.5"><span class="inline-flex items-center gap-1 rounded-[5px] border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Practica</span></div></div></a>
<a class="group block overflow-hidden rounded-[10px] border border-border bg-card" href="/en/event/cambio-de-frente-uuid"><div class="flex flex-col gap-1.5 p-3"><div class="flex flex-wrap items-baseline gap-2"><span class="font-mono text-[13px] font-semibold tracking-[0.02em] text-foreground">20:00 — 22:00</span><span data-testid="status-chip-scheduled" class="inline-flex items-center gap-1 rounded font-semibold uppercase tracking-wider border border-border bg-muted text-muted-foreground py-0.5 ml-auto shrink-0 text-[0.65rem] px-2"><svg class="lucide lucide-calendar-clock h-2.5 w-2.5 shrink-0"></svg>Regular schedule</span></div><h3 class="line-clamp-2 text-[15px] font-semibold leading-[1.3] tracking-[-0.01em] text-foreground">CAMBIO DE FRENTE</h3><div class="mt-0.5 flex flex-wrap gap-1.5"><span class="inline-flex items-center gap-1 rounded-[5px] border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Workshop</span></div></div></a>
</div>
</div>
<div class="date-section">
<span class="font-bold tabular-nums text-[var(--accent-gold)]">19</span><span class="text-sm text-muted-foreground">Sunday<span class="mx-1 opacity-50">/</span>July</span>
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
<a class="group block overflow-hidden rounded-[10px] border border-border bg-card" href="/en/event/aff759ed-bb6b-4d2c-8bb6-7ee9df6467d0"><div class="flex flex-col gap-1.5 p-3"><div class="flex flex-wrap items-baseline gap-2"><span class="font-mono text-[13px] font-semibold tracking-[0.02em] text-foreground">5:00 — 9:00</span><span data-testid="status-chip-scheduled" class="inline-flex items-center gap-1 rounded font-semibold uppercase tracking-wider border border-border bg-muted text-muted-foreground py-0.5 ml-auto shrink-0 text-[0.65rem] px-2"><svg class="lucide lucide-calendar-clock h-2.5 w-2.5 shrink-0"></svg>Regular schedule</span></div><h3 class="line-clamp-2 text-[15px] font-semibold leading-[1.3] tracking-[-0.01em] text-foreground">After House Tango de madrugada</h3><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-map-pin h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">Espacio Almagro</span></div><div class="flex min-w-0 items-center gap-1.5 text-[12.5px] text-muted-foreground"><svg class="lucide lucide-music h-3.5 w-3.5 shrink-0 opacity-55"></svg><span class="truncate">TDJ: Norma juarez</span></div><div class="mt-0.5 flex flex-wrap gap-1.5"><span class="inline-flex items-center gap-1 rounded-[5px] border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Milonga</span></div></div></a>
</div>
</div>
</body></html>
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_gotango.py`:

```python
from pathlib import Path

from app import gotango

FIXTURE = Path(__file__).parent / "fixtures" / "gotango_buenos_aires.html"


def test_slugify_lowercases_and_hyphenates():
    assert gotango._slugify("Buenos Aires") == "buenos-aires"
    assert gotango._slugify("St. Petersburg") == "st-petersburg"
    assert gotango._slugify("Tel Aviv") == "tel-aviv"
    assert gotango._slugify("Kyiv") == "kyiv"


def test_gotango_city_url_uses_slug():
    assert gotango.gotango_city_url("Buenos Aires") == "https://www.gotango.today/en/buenos-aires"


def test_parse_events_extracts_fields_and_filters_by_type():
    html = FIXTURE.read_text(encoding="utf-8")
    dates = ["2026-07-18", "2026-07-19"]

    events = gotango._parse_events(html, dates)

    assert len(events) == 4  # 3 kept on the 18th (Workshop filtered out) + 1 on the 19th
    names = [e.name for e in events]
    assert "CAMBIO DE FRENTE" not in names  # Workshop type filtered out

    first = events[0]
    assert first.name == "After House Tango de madrugada"
    assert first.time == "5:00 — 9:00"
    assert first.venue == "Espacio Almagro"
    assert first.dj == "Norma juarez"  # "TDJ: " prefix stripped
    assert first.confidence == "high"
    assert first.notes == "Regular schedule"
    assert first.date == "2026-07-18"
    assert first.source_url == "https://www.gotango.today/en/event/ab5f469a-011c-4667-ad81-5329a3fb8dd7"

    no_dj_event = next(e for e in events if e.name == "La Maria Rolera")
    assert no_dj_event.dj is None
    assert no_dj_event.date == "2026-07-18"

    practica_event = next(e for e in events if e.name == "PractiCuir")
    assert practica_event.dj == "Anahí Carballo"
    assert practica_event.date == "2026-07-18"

    second_date_events = [e for e in events if e.date == "2026-07-19"]
    assert len(second_date_events) == 1
    assert second_date_events[0].name == "After House Tango de madrugada"
    assert second_date_events[0].source_url == "https://www.gotango.today/en/event/aff759ed-bb6b-4d2c-8bb6-7ee9df6467d0"


def test_parse_events_returns_empty_list_for_no_grids():
    events = gotango._parse_events("<html><body>no events here</body></html>", ["2026-07-18"])
    assert events == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_gotango.py -v`
Expected: FAIL — `app/gotango.py` doesn't exist yet (`ModuleNotFoundError`).

- [ ] **Step 4: Create `app/gotango.py`**

```python
import re

import httpx
from bs4 import BeautifulSoup

from .models import MilongaEvent

_ALLOWED_TYPES = {"milonga", "practica"}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _slugify(city: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")


def gotango_city_url(city: str) -> str:
    return f"https://www.gotango.today/en/{_slugify(city)}"


def _classes(tag) -> list[str]:
    return tag.get("class") or []


def _find_type_tag(card) -> str | None:
    container = card.find(
        lambda t: t.name == "div" and "mt-0.5" in _classes(t) and "gap-1.5" in _classes(t)
    )
    if not container:
        return None
    span = container.find("span")
    return span.get_text(strip=True) if span else None


def _find_time_and_status(card) -> tuple[str | None, str | None]:
    container = card.find(lambda t: t.name == "div" and "items-baseline" in _classes(t))
    if not container:
        return None, None
    time_span = container.find(lambda t: t.name == "span" and "font-mono" in _classes(t))
    status_span = container.find(attrs={"data-testid": True})
    return (
        time_span.get_text(strip=True) if time_span else None,
        status_span.get_text(strip=True) if status_span else None,
    )


def _find_icon_sibling_text(card, icon_class: str) -> str | None:
    icon = card.find(lambda t: t.name == "svg" and icon_class in _classes(t))
    if not icon:
        return None
    span = icon.find_next_sibling("span")
    return span.get_text(strip=True) if span else None


def _parse_card(card, event_date: str) -> MilongaEvent | None:
    name_tag = card.find("h3")
    if not name_tag:
        return None
    name = name_tag.get_text(strip=True)

    event_type = _find_type_tag(card)
    if not event_type or event_type.lower() not in _ALLOWED_TYPES:
        return None

    time_text, status_text = _find_time_and_status(card)
    venue = _find_icon_sibling_text(card, "lucide-map-pin")

    dj_text = _find_icon_sibling_text(card, "lucide-music")
    dj = None
    if dj_text:
        dj = dj_text.removeprefix("TDJ: ").strip() or None

    href = card.get("href") or ""
    source_url = f"https://www.gotango.today{href}" if href.startswith("/") else href

    return MilongaEvent(
        name=name,
        time=time_text,
        venue=venue,
        address=None,
        price=None,
        dj=dj,
        source_url=source_url,
        confidence="high",
        notes=status_text,
        date=event_date,
    )


def _parse_events(html: str, dates: list[str]) -> list[MilongaEvent]:
    soup = BeautifulSoup(html, "html.parser")
    grids = soup.find_all(
        lambda t: t.name == "div" and "grid" in _classes(t) and "gap-4" in _classes(t)
    )

    events: list[MilongaEvent] = []
    for event_date, grid in zip(dates, grids):
        for card in grid.find_all("a", recursive=False):
            event = _parse_card(card, event_date)
            if event:
                events.append(event)
    return events


async def _fetch_gotango_html(slug: str, date_from: str, date_to: str) -> str | None:
    """Returns the rendered HTML if gotango.today covers this city, None if it 404s."""
    url = f"https://www.gotango.today/en/{slug}?from={date_from}&to={date_to}"

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            direct = await client.get(url, headers=_HEADERS)
    except Exception:
        return None
    if direct.status_code != 200:
        return None

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            rendered = await client.get(
                f"https://r.jina.ai/{url}",
                headers={**_HEADERS, "X-Return-Format": "html"},
            )
            rendered.raise_for_status()
    except Exception:
        return None
    return rendered.text


async def fetch_gotango_events(city: str, dates: list[str]) -> list[MilongaEvent] | None:
    """
    Returns None if gotango.today doesn't cover this city.
    Returns a list (possibly empty) of MilongaEvent if it does — an empty
    list means "covered, but genuinely nothing scheduled" for these dates.
    """
    slug = _slugify(city)
    html = await _fetch_gotango_html(slug, dates[0], dates[-1])
    if html is None:
        return None
    return _parse_events(html, dates)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_gotango.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests (previous 67 + 4 new = 71) PASS, no regressions.

- [ ] **Step 7: Commit**

```bash
git add app/gotango.py tests/test_gotango.py tests/fixtures/gotango_buenos_aires.html
git commit -m "feat: add gotango.today connector as an LLM-free milonga data source"
```

---

### Task 2: Wire `fetch_gotango_events` into `run_milonga_agent`

**Files:**
- Modify: `app/agent.py` (import, `run_milonga_agent`)
- Test: Create `tests/test_agent.py`

**Interfaces:**
- Consumes: `fetch_gotango_events(city, dates) -> list[MilongaEvent] | None` and `gotango_city_url(city) -> str` from Task 1 (already committed).
- No new functions produced — this task only changes `run_milonga_agent`'s control flow.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agent.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agent.py -v`
Expected: FAIL — `agent.fetch_gotango_events` doesn't exist as an attribute yet (`AttributeError` from `monkeypatch.setattr`), since it isn't imported into `app/agent.py`.

- [ ] **Step 3: Wire the import and the new branch**

In `app/agent.py`, change the import block:

```python
from .tools import read_website, read_ics
from .models import MilongaEvent, MilongaResponse
from . import site_db
from .redis_client import get_redis as _get_redis, _ttl_until_midnight
```

to:

```python
from .tools import read_website, read_ics
from .models import MilongaEvent, MilongaResponse
from . import site_db
from .gotango import fetch_gotango_events, gotango_city_url
from .redis_client import get_redis as _get_redis, _ttl_until_midnight
```

Then, in `run_milonga_agent`, change:

```python
    if not city_found:
        return MilongaResponse(
            city=city,
            date=date,
            events=[],
            uncertainties=[],
            sources_found=[],
            sources_checked=[],
            city_found=False,
        )

    known_sites = await site_db.get_schedule_sites(canonical_city)
```

to:

```python
    if not city_found:
        return MilongaResponse(
            city=city,
            date=date,
            events=[],
            uncertainties=[],
            sources_found=[],
            sources_checked=[],
            city_found=False,
        )

    gotango_events = await fetch_gotango_events(canonical_city, dates)
    if gotango_events is not None:
        gotango_url = gotango_city_url(canonical_city)
        result = MilongaResponse(
            city=canonical_city,
            date=date,
            events=gotango_events,
            uncertainties=[],
            sources_found=[gotango_url],
            sources_checked=[gotango_url],
            city_found=True,
        )
        if r:
            try:
                await r.set(cache_key, result.model_dump_json(), ex=_ttl_until_midnight())
            except Exception:
                pass
        return result

    known_sites = await site_db.get_schedule_sites(canonical_city)
```

(`r` and `cache_key` are already in scope at this point in the function — defined earlier in `run_milonga_agent` for the cache-read check, unchanged by this task.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agent.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests PASS, no regressions (previous 71 + 2 new = 73).

- [ ] **Step 6: Commit**

```bash
git add app/agent.py tests/test_agent.py
git commit -m "feat: try gotango.today before the Gemini search/extraction pipeline"
```

---

### Task 3: Manual verification (real gotango.today, real bot)

This task has no code changes — it's a pre-deploy checklist. The parsing logic is tested against a real (trimmed) fixture, but gotango.today's live markup can drift, and this is the first time the bot's actual `/find` flow exercises this code path end-to-end against the live internet.

- [ ] **Step 1: Deploy to a test bot or a low-traffic window**

- [ ] **Step 2: Search a city gotango.today covers**

Send `Buenos Aires` (or another city confirmed covered during design research, e.g. `New York`). Confirm real events appear with sensible name/time/venue/DJ, and that the response feels fast (no Gemini search/extraction latency — should be noticeably quicker than a search-pipeline response).

- [ ] **Step 3: Search a city gotango.today does not cover**

Send `Moscow` (confirmed 404 during design research) or any other clearly-uncovered city. Confirm the bot falls through to the existing Gemini pipeline and behaves exactly as before this change (same latency profile, same result quality) — i.e., confirm no regression for uncovered cities.

- [ ] **Step 4: Search a gotango.today city with no events in the requested range**

If a currently-quiet covered city can be found (or by the time of testing, Buenos Aires' near-term dates happen to be sparse), confirm the bot shows the normal "no events found" message rather than erroring or incorrectly falling through to the Gemini pipeline (a covered-but-empty result must still short-circuit, per the spec).

- [ ] **Step 5: Confirm event type filtering**

For a covered city with a known workshop/festival listed on gotango.today around the test dates, confirm the bot's results only include milongas/practicas — no workshops or shows leak into the response.

- [ ] **Step 6: Confirm `/stats` "quality" numbers aren't broken**

Check the admin `/stats` command after a few gotango.today-sourced searches — confirm `result_ok`/`result_empty`/`result_notfound` counts still increment sensibly (this logic lives in `bot/main.py`'s `_run_search`, unmodified by this plan, but worth a sanity check since it's the first time `MilongaResponse.events` can be non-empty without ever calling Gemini's extraction).
