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
    updated_at: str
    districts: list[DistrictRent]
