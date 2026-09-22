from decimal import Decimal, ROUND_HALF_UP

from app.core.tax_rates import MONEY_QUANT, TAX_YEAR
from app.schemas.planner import (
    ApartmentInput,
    ApartmentResult,
    BudgetCalculationRequest,
    BudgetCalculationResponse,
    BudgetIncome,
    BudgetTotals,
    EmploymentIncome,
    MoveInInput,
    MoveInResult,
    UtilitiesResult,
    Warning,
)
from app.services.tax_service import calculate_tooleping


ZERO = Decimal("0")


def calculate_budget(request: BudgetCalculationRequest) -> BudgetCalculationResponse:
    if isinstance(request.income, EmploymentIncome):
        employment = calculate_tooleping(
            request.income.gross_monthly_income,
            request.income.pension_pillar_rate,
        )
        net_income = _decimal(employment.net_income)
        income = BudgetIncome(
            kind="employment",
            net_monthly_income=_money(net_income),
            tax_year=TAX_YEAR,
        )
    else:
        net_income = request.income.net_monthly_income
        income = BudgetIncome(
            kind="manual_net",
            net_monthly_income=_money(net_income),
            tax_year=None,
        )

    available = net_income - request.monthly_non_housing - request.monthly_savings
    share_limit = _round_money(net_income * request.housing_share)
    allowance = max(ZERO, min(available, share_limit))

    warnings: list[Warning] = []
    if available < ZERO:
        warnings.append(Warning(code="commitments_exceed_income"))

    apartment = None
    if request.apartment is not None:
        apartment, apartment_warnings = _calculate_apartment(
            request.apartment, available, allowance
        )
        warnings.extend(apartment_warnings)

    return BudgetCalculationResponse(
        income=income,
        budget=BudgetTotals(
            monthly_non_housing=_money(request.monthly_non_housing),
            monthly_savings=_money(request.monthly_savings),
            housing_share=float(request.housing_share),
            available_after_commitments=_money(available),
            share_limit=_money(share_limit),
            housing_allowance=_money(allowance),
        ),
        apartment=apartment,
        warnings=warnings,
    )


def _calculate_apartment(
    apartment: ApartmentInput,
    available: Decimal,
    allowance: Decimal,
) -> tuple[ApartmentResult, list[Warning]]:
    rent = apartment.rent
    summer = apartment.utilities.summer
    winter = apartment.utilities.winter
    warnings: list[Warning] = []

    summer_total = _round_money(rent + summer) if summer is not None else None
    winter_total = _round_money(rent + winter) if winter is not None else None
    summer_remainder = (
        _round_money(available - summer_total) if summer_total is not None else None
    )
    winter_remainder = (
        _round_money(available - winter_total) if winter_total is not None else None
    )

    if summer_total is None or winter_total is None:
        fit = "unknown"
        warnings.append(Warning(code="utilities_incomplete"))
    else:
        lower = min(summer_total, winter_total)
        upper = max(summer_total, winter_total)
        if upper <= allowance:
            fit = "within_budget"
        elif lower <= allowance:
            fit = "seasonal_risk"
        else:
            fit = "over_budget"

    move_in = None
    if apartment.move_in is not None:
        move_in, move_in_incomplete = _calculate_move_in(apartment.move_in)
        if move_in_incomplete:
            warnings.append(Warning(code="move_in_incomplete"))

    return (
        ApartmentResult(
            rent=_money(rent),
            utilities=UtilitiesResult(
                summer=_money_optional(summer),
                winter=_money_optional(winter),
                basis=apartment.utilities.basis,
            ),
            summer_total=_money_optional(summer_total),
            winter_total=_money_optional(winter_total),
            summer_remainder=_money_optional(summer_remainder),
            winter_remainder=_money_optional(winter_remainder),
            fit=fit,
            move_in=move_in,
        ),
        warnings,
    )


def _calculate_move_in(move_in: MoveInInput) -> tuple[MoveInResult, bool]:
    components: list[tuple[str, Decimal | None]] = [
        ("first_rent", move_in.first_rent),
        ("deposit", move_in.deposit),
        ("broker_fee", move_in.broker_fee),
        ("setup", move_in.setup),
    ]
    missing = [name for name, value in components if value is None]
    known_subtotal = sum(
        (value for _, value in components if value is not None), start=ZERO
    )
    cash_needed = known_subtotal if not missing else None

    return (
        MoveInResult(
            cash_needed=_money_optional(cash_needed),
            known_subtotal=_money(known_subtotal),
            missing_components=missing,
            refundable_deposit=_money_optional(move_in.deposit),
        ),
        bool(missing),
    )


def _decimal(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> float:
    return float(_round_money(value))


def _money_optional(value: Decimal | None) -> float | None:
    return None if value is None else _money(value)
