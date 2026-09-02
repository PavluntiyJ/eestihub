from datetime import date

from pydantic import BaseModel


class DistrictRent(BaseModel):
    name: str
    avg_rent_1room: int
    avg_rent_2room: int
    avg_rent_3room: int
    avg_utilities: int
    lat: float
    lon: float


class HousingRentsResponse(BaseModel):
    city: str
    updated_at: date
    districts: list[DistrictRent]


class RentTrendPoint(BaseModel):
    captured_on: date
    avg_rent_1room: int
    avg_rent_2room: int
    avg_rent_3room: int
    avg_utilities: int | None
    source: str


class DistrictRentTrend(BaseModel):
    name: str
    points: list[RentTrendPoint]


class HousingTrendsResponse(BaseModel):
    city: str
    districts: list[DistrictRentTrend]
