from datetime import date
from typing import Literal

from pydantic import BaseModel


class DistrictContext(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float
    rent: int | None
    observed_on: date | None
    source_url: str | None
    basis: Literal['published_aggregate', 'legacy_estimate', 'unknown']
    freshness: Literal['current', 'stale', 'unknown']
    legacy_utilities: int | None


class DistrictsResponse(BaseModel):
    rooms: Literal[1, 2, 3]
    districts: list[DistrictContext]
