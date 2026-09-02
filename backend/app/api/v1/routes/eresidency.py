from fastapi import APIRouter

from app.schemas.eresidency import (
    EResidencyCalculationRequest,
    EResidencyCalculationResponse,
)
from app.services.eresidency_service import calculate_eresidency_costs


router = APIRouter(tags=["e-residency"])


@router.post("/calculate-eresidency", response_model=EResidencyCalculationResponse)
def calculate_eresidency(
    request: EResidencyCalculationRequest,
) -> EResidencyCalculationResponse:
    return calculate_eresidency_costs(request)
