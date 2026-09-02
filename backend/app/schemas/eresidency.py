from pydantic import BaseModel, Field

from app.core.fees import MONTHLY_ACCOUNTING_FEE_DEFAULT


class EResidencyCalculationRequest(BaseModel):
    expected_monthly_revenue: float = Field(gt=0)
    monthly_accounting_fee: float = Field(
        default=float(MONTHLY_ACCOUNTING_FEE_DEFAULT),
        ge=0,
    )


class EResidencyCostLine(BaseModel):
    name: str
    amount: float


class EResidencyCalculationResponse(BaseModel):
    input: EResidencyCalculationRequest
    setup_breakdown: list[EResidencyCostLine]
    monthly_running_cost: float
    first_year_total_cost: float
    break_even_monthly_revenue: float
    first_year_revenue: float
    first_year_surplus: float
