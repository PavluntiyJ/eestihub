from decimal import Decimal, ROUND_HALF_UP

from app.core.fees import (
    CONTACT_PERSON_ANNUAL_FEE_DEFAULT,
    E_RESIDENCY_APPLICATION_FEE,
    MONEY_QUANT,
    ONLINE_OU_REGISTRATION_FEE,
    WHOLE_EURO_QUANT,
)
from app.schemas.eresidency import (
    EResidencyCalculationRequest,
    EResidencyCalculationResponse,
    EResidencyCostLine,
)


MONTHS_PER_YEAR = Decimal("12")


def calculate_eresidency_costs(
    request: EResidencyCalculationRequest,
) -> EResidencyCalculationResponse:
    monthly_revenue = Decimal(str(request.expected_monthly_revenue))
    monthly_accounting = Decimal(str(request.monthly_accounting_fee))
    setup_total = (
        E_RESIDENCY_APPLICATION_FEE
        + ONLINE_OU_REGISTRATION_FEE
        + CONTACT_PERSON_ANNUAL_FEE_DEFAULT
    )
    first_year_total = setup_total + monthly_accounting * MONTHS_PER_YEAR
    first_year_revenue = monthly_revenue * MONTHS_PER_YEAR

    return EResidencyCalculationResponse(
        input=request,
        setup_breakdown=[
            EResidencyCostLine(
                name="eresidency_application",
                amount=_money(E_RESIDENCY_APPLICATION_FEE),
            ),
            EResidencyCostLine(
                name="ou_online_registration",
                amount=_money(ONLINE_OU_REGISTRATION_FEE),
            ),
            EResidencyCostLine(
                name="contact_person_first_year",
                amount=_money(CONTACT_PERSON_ANNUAL_FEE_DEFAULT),
            ),
        ],
        monthly_running_cost=_money(monthly_accounting),
        first_year_total_cost=_money(first_year_total),
        break_even_monthly_revenue=_whole_euros(first_year_total / MONTHS_PER_YEAR),
        first_year_revenue=_money(first_year_revenue),
        first_year_surplus=_money(first_year_revenue - first_year_total),
    )


def _money(value: Decimal) -> float:
    return float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _whole_euros(value: Decimal) -> float:
    return float(value.quantize(WHOLE_EURO_QUANT, rounding=ROUND_HALF_UP))
