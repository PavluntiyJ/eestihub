from fastapi import APIRouter

from app.schemas.taxes import TaxCalculationRequest, TaxCalculationResponse
from app.services.tax_service import compare_regimes


router = APIRouter(tags=["taxes"])


@router.post("/calculate-taxes", response_model=TaxCalculationResponse)
def calculate_taxes(request: TaxCalculationRequest) -> TaxCalculationResponse:
    return compare_regimes(request)
