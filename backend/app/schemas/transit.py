from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class NearbyRoute(BaseModel):
    id: str
    short_name: str | None
    long_name: str | None
    mode: Literal["tram", "bus", "trolleybus", "other"]


class NearbyStop(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float
    straight_line_distance_m: int
    routes: list[NearbyRoute]


class TransitProvenance(BaseModel):
    source_url: str
    attribution: str
    license_url: str
    data_license: str
    transformation: str
    fetched_at: datetime
    checked_at: datetime
    source_last_modified: datetime | None
    calendar_start: date | None
    calendar_end: date | None
    freshness: Literal["current", "stale", "unknown"]


class NearbyTransitResponse(BaseModel):
    radius_m: int = 800
    limit: int = 20
    service_date: date
    timezone: str = "Europe/Tallinn"
    stops: list[NearbyStop]
    feed: TransitProvenance
