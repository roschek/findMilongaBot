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
