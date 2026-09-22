from decimal import Decimal
from math import isfinite
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.tax_rates import PENSION_PILLAR_RATES

MAX_MONEY = Decimal("1000000")

UtilityBasis = Literal["user_bill", "user_estimate", "legacy_assumption", "unknown"]
Fit = Literal["within_budget", "seasonal_risk", "over_budget", "unknown"]
WarningCode = Literal[
    "commitments_exceed_income",
    "utilities_incomplete",
    "move_in_incomplete",
]
MissingComponent = Literal["first_rent", "deposit", "broker_fee", "setup"]


def _to_decimal(value: object) -> object:
    # JSON numbers arrive as binary floats; parse them from their decimal text
    # so 0.1 stays 0.1 instead of 0.1000000000000000055511151231257827.
    # Booleans are rejected explicitly: bool subclasses int, so without this
    # check True/False would silently become 1/0 money amounts.
    if isinstance(value, bool):
        raise ValueError("value must be a number, not a boolean")
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("value must be a finite number")
        return Decimal(str(value))
    if isinstance(value, int):
        return Decimal(value)
    return value


Money = Annotated[
    Decimal,
    BeforeValidator(_to_decimal),
    Field(ge=0, le=MAX_MONEY, decimal_places=2),
]
PositiveMoney = Annotated[
    Decimal,
    BeforeValidator(_to_decimal),
    Field(gt=0, le=MAX_MONEY, decimal_places=2),
]
HousingShare = Annotated[
    Decimal,
    BeforeValidator(_to_decimal),
    Field(ge=0, le=1, decimal_places=4),
]


class EmploymentIncome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["employment"]
    gross_monthly_income: PositiveMoney
    pension_pillar_rate: Decimal

    @field_validator("pension_pillar_rate", mode="before")
    @classmethod
    def parse_pension_pillar_rate(cls, value: object) -> object:
        return _to_decimal(value)

    @field_validator("pension_pillar_rate")
    @classmethod
    def validate_pension_pillar_rate(cls, value: Decimal) -> Decimal:
        if value not in PENSION_PILLAR_RATES:
            raise ValueError("must be one of 0.00, 0.02, 0.04, 0.06")
        return value


class ManualNetIncome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["manual_net"]
    net_monthly_income: Money


Income = Annotated[
    EmploymentIncome | ManualNetIncome,
    Field(discriminator="kind"),
]


class UtilitiesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required but nullable: the keys must be present, explicit null marks
    # an unknown seasonal amount.
    summer: Money | None
    winter: Money | None
    basis: UtilityBasis

    @model_validator(mode="after")
    def validate_amounts_match_basis(self) -> "UtilitiesInput":
        if self.basis == "unknown":
            if self.summer is not None or self.winter is not None:
                raise ValueError("unknown utilities must have null amounts")
        elif self.summer is None and self.winter is None:
            raise ValueError("utilities need at least one seasonal amount")
        return self


class MoveInInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required but nullable: the keys must be present, explicit null marks
    # an unknown cost component.
    first_rent: Money | None
    deposit: Money | None
    broker_fee: Money | None
    setup: Money | None


class ApartmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rent: Money
    utilities: UtilitiesInput
    move_in: MoveInInput | None


class BudgetCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income: Income
    monthly_non_housing: Money
    monthly_savings: Money
    housing_share: HousingShare
    apartment: ApartmentInput | None = None


class Warning(BaseModel):
    code: WarningCode


class BudgetIncome(BaseModel):
    kind: Literal["employment", "manual_net"]
    net_monthly_income: float
    tax_year: int | None


class BudgetTotals(BaseModel):
    monthly_non_housing: float
    monthly_savings: float
    housing_share: float
    available_after_commitments: float
    share_limit: float
    housing_allowance: float


class UtilitiesResult(BaseModel):
    summer: float | None
    winter: float | None
    basis: UtilityBasis


class MoveInResult(BaseModel):
    cash_needed: float | None
    known_subtotal: float
    missing_components: list[MissingComponent]
    refundable_deposit: float | None


class ApartmentResult(BaseModel):
    rent: float
    utilities: UtilitiesResult
    summer_total: float | None
    winter_total: float | None
    summer_remainder: float | None
    winter_remainder: float | None
    fit: Fit
    move_in: MoveInResult | None


class BudgetCalculationResponse(BaseModel):
    schema_version: Literal[1] = 1
    income: BudgetIncome
    budget: BudgetTotals
    apartment: ApartmentResult | None
    warnings: list[Warning]
