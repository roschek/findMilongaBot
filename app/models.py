from pydantic import BaseModel
from typing import Optional


class MilongaEvent(BaseModel):
    name: str
    time: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    price: Optional[str] = None
    dj: Optional[str] = None
    source_url: str
    confidence: str  # "high" | "medium" | "low"
    notes: Optional[str] = None
    date: Optional[str] = None  # which date this event is on


class MilongaResponse(BaseModel):
    city: str
    date: str
    events: list[MilongaEvent]
    uncertainties: list[str]
    sources_found: list[str] = []
    sources_checked: list[str]
    cached: bool = False
    city_found: bool = True  # False when city doesn't exist
