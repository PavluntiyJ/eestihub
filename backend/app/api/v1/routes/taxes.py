from fastapi import APIRouter

from app.schemas.taxes import TaxCalculationRequest, TaxCalculationResponse
from app.services.tax_service import compare_regimes


router = APIRouter(tags=["taxes"])


@router.post(
    "/calculate-taxes",
    response_model=TaxCalculationResponse,
    summary="Compare net income across the four Estonian regimes",
    description=(
        "Returns net income, payer cost, effective rate, a tax breakdown and "
        "any statutory constraints for tööleping, juhatuse liige, FIE and "
        "ettevõtluskonto.\n\n"
        "`equalize_by` chooses what the four regimes have in common: `gross` "
        "computes them all from the same gross income, `payer_cost` reads the "
        "input as the payer's total monthly cost and derives each regime's own "
        "gross from it. The regimes cost the payer different amounts for the "
        "same gross, so ranking them is only meaningful once a basis is fixed."
    ),
)
def calculate_taxes(request: TaxCalculationRequest) -> TaxCalculationResponse:
    return compare_regimes(request)
