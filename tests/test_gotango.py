from pathlib import Path

from app import gotango

FIXTURE = Path(__file__).parent / "fixtures" / "gotango_buenos_aires.html"


def test_slugify_lowercases_and_hyphenates():
    assert gotango._slugify("Buenos Aires") == "buenos-aires"
    assert gotango._slugify("St. Petersburg") == "st-petersburg"
    assert gotango._slugify("Tel Aviv") == "tel-aviv"
    assert gotango._slugify("Kyiv") == "kyiv"


def test_slugify_transliterates_accented_characters():
    assert gotango._slugify("São Paulo") == "sao-paulo"


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
