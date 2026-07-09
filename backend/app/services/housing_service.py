from app.schemas.housing import DistrictRent, HousingRentsResponse
from app.services.housing_data import CITY, DISTRICT_RENTS, UPDATED_AT


def get_housing_rents() -> HousingRentsResponse:
    return HousingRentsResponse(
        city=CITY,
        updated_at=UPDATED_AT,
        districts=[DistrictRent(**district._asdict()) for district in DISTRICT_RENTS],
    )
