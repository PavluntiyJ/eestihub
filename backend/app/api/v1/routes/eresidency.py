from fastapi import APIRouter

from app.schemas.eresidency import (
    EResidencyCalculationRequest,
    EResidencyCalculationResponse,
)
from app.services.eresidency_service import calculate_eresidency_costs


router = APIRouter(tags=["e-residency"])


@router.post(
    "/calculate-eresidency",
    response_model=EResidencyCalculationResponse,
    summary="First-year cost of running an e-resident OÜ",
    description=(
        "Setup fees, monthly running cost, first-year total, break-even "
        "monthly revenue and first-year surplus. A cost model only: it does "
        "not tax the revenue, so the surplus is not a post-tax figure."
    ),
)
def calculate_eresidency(
    request: EResidencyCalculationRequest,
) -> EResidencyCalculationResponse:
    return calculate_eresidency_costs(request)
