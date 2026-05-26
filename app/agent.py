import json
import asyncio
import os
from datetime import date as date_type, timedelta
from urllib.parse import urlparse

from google import genai
from google.genai import types

from .tools import read_website, read_ics
from .models import MilongaEvent, MilongaResponse
from . import site_db

SYSTEM_PROMPT = """You are a tango event research assistant.
Extract milonga events AND tango practicas for a specific city and multiple dates from the provided web page contents.

The dates to extract for are provided in the user message as a JSON array with weekday names.

STRICT DATE RULE: For each event, assign it to the correct date from the requested list.
- For recurring weekly schedules: assign to whichever requested date has the matching weekday.
- For explicitly dated events: assign to the matching date only.
- If an event's date matches NONE of the requested dates, omit it entirely.
- An empty list for a date is correct when nothing is confirmed for that date.

Return a JSON object with this exact structure:
{
  "events_by_date": {
    "2026-05-25": [
      {
        "name": "...",
        "time": "22:00" or null,
        "venue": "...",
        "address": "..." or null,
        "price": "..." or null,
        "dj": "..." or null,
        "source_url": "https://...",
        "confidence": "high" | "medium" | "low",
        "notes": "..." or null
      }
    ],
    "2026-05-26": [],
    "2026-05-27": [],
    "2026-05-28": []
  },
  "schedule_sources": ["url1", "url2"],
  "uncertainties": ["..."]
}

schedule_sources: list ONLY URLs that contain tango schedule or calendar information SPECIFICALLY for the requested city.
  Include a URL only if its content is dedicated to or explicitly covers that city's tango scene.
  EXCLUDE general multi-city aggregators that happen to mention the city among many others.
  (Include even if no events match — any site with recurring schedules for that city counts.)

confidence="high": date explicitly stated on the page.
confidence="medium": weekly schedule, weekday matches requested date.
confidence="low": some date evidence but uncertain — omit if date is clearly wrong."""


async def _normalize_city(client: genai.Client, city_input: str) -> tuple[str, bool]:
    """
    Returns (canonical_english_name, is_valid_city).
    Uses Gemini to canonicalize city names across languages and spellings.
    """
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=(
            f"What is the canonical English name of the city or town '{city_input}'?\n"
            f"If it is a real place but small (under 300k population or unlikely to have an active tango scene), "
            f"return the nearest large city instead (e.g. 'Petah Tikva' → 'Tel Aviv', 'Mytishchi' → 'Moscow').\n"
            f"If it is a real major city, reply with just the canonical English name (e.g. 'Moscow', 'Tel Aviv', 'Tbilisi').\n"
            f"If it is NOT a real place name at all, reply with exactly: UNKNOWN\n"
            f"Reply with just the city name, nothing else."
        ),
        config=types.GenerateContentConfig(temperature=0),
    )
    result = response.candidates[0].content.parts[0].text.strip().strip(".")
    if not result or result.upper() == "UNKNOWN":
        return city_input, False
    return result, True


async def _search_phase(client: genai.Client, city: str, date: str) -> tuple[list[str], list[str]]:
    """Use Gemini + Google Search to find relevant URLs."""
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=(
            f"Find 10 URLs of websites with tango milonga and practica schedules and calendars "
            f"for {city}. Include local tango association sites, event calendars, and tango portals. "
            f"Prefer direct links to schedule or calendar pages (e.g. /events, /calendar, /milongas) "
            f"rather than just homepages. Current date: {date}. "
            f"Return only a JSON list of URLs: [\"url1\", \"url2\", ...]"
        ),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0,
        ),
    )

    candidate = response.candidates[0]
    sources_found: list[str] = []

    if getattr(candidate, "grounding_metadata", None):
        for chunk in (getattr(candidate.grounding_metadata, "grounding_chunks", None) or []):
            web = getattr(chunk, "web", None)
            if web and getattr(web, "uri", None) and web.uri not in sources_found:
                sources_found.append(web.uri)

    text = "".join(p.text for p in candidate.content.parts if getattr(p, "text", None))
    try:
        start, end = text.find("["), text.rfind("]") + 1
        for url in json.loads(text[start:end]):
            if isinstance(url, str) and url not in sources_found:
                sources_found.append(url)
    except Exception:
        pass

    return sources_found, sources_found[:10]


def _probe_ics_urls(web_urls: list[str], existing_ics: list[str]) -> list[str]:
    """Generate candidate ICS feed URLs for WordPress-based event sites."""
    probes: list[str] = []
    for url in web_urls:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates = [
            f"{base}/events/feed/?ical=1",
            f"{base}/events/ical/",
        ]
        for c in candidates:
            if c not in existing_ics and c not in probes:
                probes.append(c)
    return probes


async def _fetch_pages(
    city: str, web_urls: list[str], ics_urls: list[str], dates: list[str]
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Fetch web pages and ICS feeds in parallel.
    Returns (page_contents, ics_contents, sources_checked).
    """
    # Probe WordPress ICS endpoints for web URLs
    ics_probes = _probe_ics_urls(web_urls, ics_urls)
    all_ics = list(ics_urls) + ics_probes

    page_task = asyncio.gather(*[read_website(u) for u in web_urls])
    ics_task = asyncio.gather(*[read_ics(u, dates) for u in all_ics])
    page_contents, ics_results = await asyncio.gather(page_task, ics_task)
    page_contents, ics_results = list(page_contents), list(ics_results)

    # For pages with thin content, also try /events/ sub-page (max 3 probes)
    extra_web: list[str] = []
    for url, content in zip(web_urls, page_contents):
        if len(extra_web) >= 3:
            break
        parsed = urlparse(url)
        if parsed.path.strip("/") == "" and (content.startswith("ERROR") or len(content) < 1500):
            candidate = url.rstrip("/") + "/events/"
            if candidate not in web_urls and candidate not in extra_web:
                extra_web.append(candidate)

    extra_contents: list[str] = []
    if extra_web:
        extra_contents = list(await asyncio.gather(*[read_website(u) for u in extra_web]))

    all_web = list(web_urls) + extra_web
    page_contents = page_contents + extra_contents

    # Drop probes that errored (not real feeds)
    valid_ics: list[str] = []
    valid_ics_results: list[str] = []
    for url, result in zip(all_ics, ics_results):
        if url in ics_probes and result.startswith("ERROR"):
            continue
        valid_ics.append(url)
        valid_ics_results.append(result)
    ics_urls = valid_ics
    ics_results = valid_ics_results

    sources_checked = list(all_web)

    for url, content in zip(web_urls, page_contents):
        if content.startswith("ERROR"):
            site_db.mark_failure(city, url)
        else:
            site_db.mark_success(city, url)

    extra_ics_urls: list[str] = []
    for content in page_contents:
        if "CALENDAR_FEEDS_FOUND:" in content:
            for line in content.splitlines():
                line = line.strip()
                if (
                    line.startswith("http")
                    and (".ics" in line or "calendar.google.com/calendar/ical" in line)
                    and line not in ics_urls
                    and line not in extra_ics_urls
                ):
                    extra_ics_urls.append(line)

    if extra_ics_urls:
        extra_results = list(await asyncio.gather(*[read_ics(u, dates) for u in extra_ics_urls]))
        ics_urls = list(ics_urls) + extra_ics_urls
        ics_results = ics_results + extra_results

    for url, result in zip(ics_urls, ics_results):
        sources_checked.append(url)
        if result.startswith("ERROR"):
            site_db.mark_ics_failure(city, url)
        else:
            site_db.mark_ics_success(city, url)

    return page_contents, ics_results, sources_checked, all_web


async def _extract_events(
    client: genai.Client,
    city: str,
    dates: list[str],
    web_urls: list[str],
    page_contents: list[str],
    ics_urls: list[str],
    ics_contents: list[str],
) -> tuple[list[MilongaEvent], list[str], list[str]]:
    """Single LLM call. Returns (events, uncertainties, schedule_sources)."""
    pages_text = ""
    for url, content in zip(web_urls, page_contents):
        pages_text += f"\n\n=== SOURCE: {url} ===\n{content[:8000]}"
    for url, ics in zip(ics_urls, ics_contents):
        pages_text += f"\n\n=== ICS CALENDAR: {url} ===\n{ics}"

    dates_with_weekdays = [
        f"{d} ({date_type.fromisoformat(d).strftime('%A')})" for d in dates
    ]

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"City: {city}\n"
            f"Dates: {json.dumps(dates)}\n"
            f"Weekdays: {', '.join(dates_with_weekdays)}\n\n"
            f"Page contents:\n{pages_text}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
        ),
    )

    final_text = "".join(
        p.text for p in response.candidates[0].content.parts if getattr(p, "text", None)
    )

    try:
        start = final_text.find("{")
        end = final_text.rfind("}") + 1
        data = json.loads(final_text[start:end])
    except Exception:
        data = {"events_by_date": {}, "uncertainties": ["Agent returned unparseable response"], "schedule_sources": []}

    events: list[MilongaEvent] = []
    for d, ev_list in data.get("events_by_date", {}).items():
        for e in ev_list:
            try:
                event = MilongaEvent(**e, date=d)
                if not (event.confidence == "low" and _is_wrong_date(event.notes, d)):
                    events.append(event)
            except Exception:
                pass

    return events, data.get("uncertainties", []), data.get("schedule_sources", [])


def _is_wrong_date(notes: str | None, date: str) -> bool:
    if not notes:
        return False
    notes_lower = notes.lower()
    return (
        "one day" in notes_lower
        or "different date" in notes_lower
        or "not on" in notes_lower
        or (date not in notes and "wrong date" in notes_lower)
    )


def _productive_ics(ics_urls: list[str], ics_contents: list[str]) -> list[str]:
    return [
        url for url, content in zip(ics_urls, ics_contents)
        if not content.startswith("ERROR") and not content.startswith("No events found")
    ]


async def _run_with_urls(
    client: genai.Client,
    city: str,
    dates: list[str],
    web_urls: list[str],
    known_ics: list[str],
) -> tuple[list[MilongaEvent], list[str], list[str], list[str], list[str], list[str]]:
    """Returns (events, uncertainties, sources_checked, all_ics_urls, ics_contents, schedule_sources)."""
    page_contents, ics_contents, sources_checked, all_web = await _fetch_pages(city, web_urls, known_ics, dates)

    all_ics_urls = list(known_ics)
    for url in sources_checked:
        if (".ics" in url or "calendar.google.com/calendar/ical" in url) and url not in all_ics_urls:
            all_ics_urls.append(url)

    events, uncertainties, schedule_sources = await _extract_events(
        client, city, dates, all_web, page_contents, all_ics_urls, ics_contents
    )
    return events, uncertainties, sources_checked, all_ics_urls, ics_contents, schedule_sources


def _save_sites(city: str, events: list[MilongaEvent], schedule_sources: list[str],
                ics_urls: list[str], ics_contents: list[str]) -> None:
    """Save all schedule sources to DB, not just event source_urls."""
    # Web URLs: from LLM-identified schedule_sources + event source_urls
    web_urls = list(dict.fromkeys(
        schedule_sources
        + [e.source_url for e in events if e.source_url]
    ))
    web_urls = [u for u in web_urls if ".ics" not in u and "calendar.google.com/calendar/ical" not in u]

    ics = _productive_ics(ics_urls, ics_contents)
    if web_urls or ics:
        site_db.save_productive_sites(city, web_urls, ics)


async def run_milonga_agent(city: str, date: str, days_ahead: int = 3) -> MilongaResponse:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Build date range: today + days_ahead
    start = date_type.fromisoformat(date)
    dates = [str(start + timedelta(days=i)) for i in range(days_ahead + 1)]

    # Normalize city name and validate it exists
    canonical_city, city_found = await _normalize_city(client, city)
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

    known_sites = site_db.get_schedule_sites(canonical_city)
    known_ics = site_db.get_ics_feeds(canonical_city)

    if known_sites:
        web_known = [u for u in known_sites if ".ics" not in u and "calendar.google.com/calendar/ical" not in u]
        ics_known = list(dict.fromkeys(known_ics + [u for u in known_sites if u not in web_known]))
    else:
        web_known, ics_known = [], []

    if web_known or ics_known:
        events, uncertainties, sources_checked, all_ics_urls, ics_contents, schedule_sources = \
            await _run_with_urls(client, canonical_city, dates, web_known, ics_known)
        sources_found = web_known

        _save_sites(canonical_city, events, schedule_sources, all_ics_urls, ics_contents)

        if not events:
            # Known sites gave nothing — re-search
            fresh_found, candidate_urls = await _search_phase(client, canonical_city, date)
            sources_found = list(dict.fromkeys(web_known + fresh_found))
            search_web = [u for u in candidate_urls[:8] if ".ics" not in u]
            events, uncertainties, sources_checked, all_ics_urls, ics_contents, schedule_sources = \
                await _run_with_urls(client, canonical_city, dates, search_web, ics_known)
            _save_sites(canonical_city, events, schedule_sources, all_ics_urls, ics_contents)
    else:
        sources_found, candidate_urls = await _search_phase(client, canonical_city, date)
        search_web = [u for u in candidate_urls[:8] if ".ics" not in u]
        events, uncertainties, sources_checked, all_ics_urls, ics_contents, schedule_sources = \
            await _run_with_urls(client, canonical_city, dates, search_web, [])
        _save_sites(canonical_city, events, schedule_sources, all_ics_urls, ics_contents)

    return MilongaResponse(
        city=canonical_city,
        date=date,
        events=events,
        uncertainties=uncertainties,
        sources_found=sources_found,
        sources_checked=sources_checked,
        city_found=True,
    )
