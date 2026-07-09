from fastapi import APIRouter

from app.schemas.housing import HousingRentsResponse
from app.services.housing_service import get_housing_rents


router = APIRouter(prefix="/housing", tags=["housing"])


@router.get("/rents", response_model=HousingRentsResponse)
def housing_rents() -> HousingRentsResponse:
    return get_housing_rents()
