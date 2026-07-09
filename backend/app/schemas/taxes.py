from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.tax_rates import PENSION_PILLAR_RATES


Regime = Literal["tooleping", "juhatuse_liige", "fie", "ettevotluskonto"]


class TaxCalculationRequest(BaseModel):
    gross_monthly_income: float = Field(gt=0)
    pension_pillar_rate: float = 0.02

    @field_validator("pension_pillar_rate")
    @classmethod
    def validate_pension_pillar_rate(cls, value: float) -> float:
        if Decimal(str(value)) not in PENSION_PILLAR_RATES:
            raise ValueError("pension_pillar_rate must be one of 0.0, 0.02, 0.04, 0.06")
        return value


class TaxLine(BaseModel):
    name: str
    amount: float


class RegimeResult(BaseModel):
    regime: Regime
    label: str
    employer_total_cost: float
    gross_income: float
    breakdown: list[TaxLine]
    net_income: float
    effective_tax_rate: float


class TaxCalculationResponse(BaseModel):
    input: TaxCalculationRequest
    results: list[RegimeResult]
