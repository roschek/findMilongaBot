import os
from datetime import date as date_module
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.agent import run_milonga_agent
from app.cache import get_cached, set_cached
from app.models import MilongaResponse

load_dotenv()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    expected = os.environ.get("API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Milonga Agent API",
    description="Find tango milonga events in any city for any date.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/milongas", response_model=MilongaResponse, dependencies=[Security(_require_api_key)])
async def get_milongas(
    city: str = Query(..., description="City name, e.g. 'Buenos Aires'"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today."),
):
    city = city.strip().title()
    if not city:
        raise HTTPException(status_code=400, detail="city is required")

    target_date = date or str(date_module.today())

    cached = get_cached(city, target_date)
    if cached:
        cached.cached = True
        return cached

    result = await run_milonga_agent(city=city, date=target_date)
    set_cached(city, target_date, result)
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}
