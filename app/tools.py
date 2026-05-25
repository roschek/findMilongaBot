import asyncio
import re
from datetime import date as date_type
from html import unescape
from urllib.parse import parse_qs, quote, urlparse

import httpx
import icalendar
import recurring_ical_events
from bs4 import BeautifulSoup


def _embed_to_ics_url(url: str) -> str:
    url = unescape(url)
    if "google.com/calendar/embed" in url:
        params = parse_qs(urlparse(url).query)
        if "src" in params:
            calendar_id = params["src"][0]
            return f"https://calendar.google.com/calendar/ical/{quote(calendar_id, safe='')}/public/basic.ics"
    return url


def _extract_calendar_links(html: str) -> list[str]:
    links: list[str] = []
    for url in re.findall(r'https://(?:www\.)?google\.com/calendar/embed\?[^"\'<\s]+', html):
        ics = _embed_to_ics_url(url)
        if ics not in links:
            links.append(ics)
    for url in re.findall(r'https://calendar\.google\.com/calendar/embed\?[^"\'<\s]+', html):
        ics = _embed_to_ics_url(url)
        if ics not in links:
            links.append(ics)
    for url in re.findall(r'https?://[^\s"\'<]+\.ics[^\s"\'<]*', html):
        if url not in links:
            links.append(url)
    return links


async def read_website(url: str) -> str:
    """Fetch a webpage and return its text content. Falls back to Jina Reader for JS-heavy pages."""

    def _fetch_httpx() -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        }
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                raw_html = response.text
        except Exception as e:
            return f"ERROR: could not fetch {url}: {e}"

        calendar_links = _extract_calendar_links(raw_html)
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)[:10000]
        if calendar_links:
            text += "\n\nCALENDAR_FEEDS_FOUND:\n" + "\n".join(calendar_links)
        return text

    def _fetch_jina() -> str:
        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                response = client.get(
                    f"https://r.jina.ai/{url}",
                    headers={"Accept": "text/plain"},
                )
                return response.text[:10000]
        except Exception as e:
            return f"ERROR: Jina fetch failed: {e}"

    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(None, _fetch_httpx)

    if content.startswith("ERROR") or len(content) < 500:
        jina = await loop.run_in_executor(None, _fetch_jina)
        if not jina.startswith("ERROR") and len(jina) > len(content):
            return jina

    return content


async def read_ics(url: str, dates: list[str]) -> str:
    """Fetch and parse an ICS/iCal file, returning events for a list of dates.
    Also accepts Google Calendar embed URLs — converts them to ICS automatically."""
    ics_url = _embed_to_ics_url(url)

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(ics_url)
            response.raise_for_status()
    except Exception as e:
        return f"ERROR: could not fetch ICS from {ics_url}: {e}"

    try:
        cal = icalendar.Calendar.from_ical(response.content)
    except Exception as e:
        return f"ERROR: could not parse ICS: {e}"

    all_lines: list[str] = []
    for date in dates:
        try:
            target = date_type.fromisoformat(date)
            events = recurring_ical_events.of(cal).at(target)
        except Exception:
            continue
        if not events:
            continue
        all_lines.append(f"Events on {date}:")
        for event in events:
            name = str(event.get("SUMMARY", "Unknown"))
            dtstart = event.get("DTSTART").dt
            location = str(event.get("LOCATION", ""))
            description = str(event.get("DESCRIPTION", ""))
            time_str = dtstart.strftime("%H:%M") if hasattr(dtstart, "hour") else "time unknown"
            line = f"- {name} at {time_str}"
            if location:
                line += f" | {location}"
            all_lines.append(line)
            if description and description != "None":
                all_lines.append(f"  {description[:300]}")

    if not all_lines:
        return f"No events found in this calendar for the requested dates."

    return f"ICS Calendar {ics_url}:\n" + "\n".join(all_lines)
