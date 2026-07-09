from decimal import Decimal, ROUND_HALF_UP

from app.core.tax_rates import (
    BASIC_EXEMPTION_MONTHLY,
    EFFECTIVE_TAX_RATE_QUANT,
    ENTREPRENEUR_ACCOUNT_TAX_RATE,
    FULL_RATE,
    INCOME_TAX_RATE,
    MONEY_QUANT,
    SOCIAL_TAX_RATE,
    UNEMPLOYMENT_INSURANCE_EMPLOYEE_RATE,
    UNEMPLOYMENT_INSURANCE_EMPLOYER_RATE,
    ZERO_AMOUNT,
)
from app.schemas.taxes import (
    RegimeResult,
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxLine,
)


def calculate_tooleping(
    gross_income: Decimal | float | int, pension_pillar_rate: Decimal | float | int
) -> RegimeResult:
    gross_income = _decimal(gross_income)
    pension_pillar_rate = _decimal(pension_pillar_rate)

    employer_social_tax = gross_income * SOCIAL_TAX_RATE
    employer_unemployment = gross_income * UNEMPLOYMENT_INSURANCE_EMPLOYER_RATE
    employee_unemployment = gross_income * UNEMPLOYMENT_INSURANCE_EMPLOYEE_RATE
    pension_pillar = gross_income * pension_pillar_rate
    income_tax = _income_tax(gross_income - employee_unemployment - pension_pillar)
    employer_total_cost = gross_income + employer_social_tax + employer_unemployment
    net_income = gross_income - employee_unemployment - pension_pillar - income_tax

    return _result(
        regime="tooleping",
        label="Employment contract (Tööleping)",
        employer_total_cost=employer_total_cost,
        gross_income=gross_income,
        breakdown=[
            TaxLine(name="income_tax", amount=_money(income_tax)),
            TaxLine(
                name="unemployment_insurance_employee",
                amount=_money(employee_unemployment),
            ),
            TaxLine(name="pension_pillar_ii", amount=_money(pension_pillar)),
        ],
        net_income=net_income,
    )


def calculate_juhatuse_liige(gross_income: Decimal | float | int) -> RegimeResult:
    gross_income = _decimal(gross_income)

    employer_social_tax = gross_income * SOCIAL_TAX_RATE
    income_tax = _income_tax(gross_income)
    employer_total_cost = gross_income + employer_social_tax
    net_income = gross_income - income_tax

    return _result(
        regime="juhatuse_liige",
        label="Management board member (Juhatuse liige)",
        employer_total_cost=employer_total_cost,
        gross_income=gross_income,
        breakdown=[TaxLine(name="income_tax", amount=_money(income_tax))],
        net_income=net_income,
    )


def calculate_fie(gross_income: Decimal | float | int) -> RegimeResult:
    gross_income = _decimal(gross_income)

    social_tax = gross_income * SOCIAL_TAX_RATE
    income_tax = _income_tax(gross_income - social_tax)
    net_income = gross_income - social_tax - income_tax

    return _result(
        regime="fie",
        label="Self-employed person (FIE)",
        employer_total_cost=gross_income,
        gross_income=gross_income,
        breakdown=[
            TaxLine(name="social_tax", amount=_money(social_tax)),
            TaxLine(name="income_tax", amount=_money(income_tax)),
        ],
        net_income=net_income,
    )


def calculate_ettevotluskonto(gross_income: Decimal | float | int) -> RegimeResult:
    gross_income = _decimal(gross_income)

    business_income_tax = gross_income * ENTREPRENEUR_ACCOUNT_TAX_RATE
    net_income = gross_income - business_income_tax

    return _result(
        regime="ettevotluskonto",
        label="Entrepreneur account (Ettevõtluskonto)",
        employer_total_cost=gross_income,
        gross_income=gross_income,
        breakdown=[TaxLine(name="business_income_tax", amount=_money(business_income_tax))],
        net_income=net_income,
    )


def compare_regimes(request: TaxCalculationRequest) -> TaxCalculationResponse:
    gross_income = _decimal(request.gross_monthly_income)
    pension_pillar_rate = _decimal(request.pension_pillar_rate)

    return TaxCalculationResponse(
        input=request,
        results=[
            calculate_tooleping(gross_income, pension_pillar_rate),
            calculate_juhatuse_liige(gross_income),
            calculate_fie(gross_income),
            calculate_ettevotluskonto(gross_income),
        ],
    )


def _income_tax(income_before_basic_exemption: Decimal) -> Decimal:
    taxable_income = max(
        income_before_basic_exemption - BASIC_EXEMPTION_MONTHLY,
        ZERO_AMOUNT,
    )
    return taxable_income * INCOME_TAX_RATE


def _result(
    regime: str,
    label: str,
    employer_total_cost: Decimal,
    gross_income: Decimal,
    breakdown: list[TaxLine],
    net_income: Decimal,
) -> RegimeResult:
    return RegimeResult(
        regime=regime,
        label=label,
        employer_total_cost=_money(employer_total_cost),
        gross_income=_money(gross_income),
        breakdown=breakdown,
        net_income=_money(net_income),
        effective_tax_rate=_effective_tax_rate(net_income, employer_total_cost),
    )


def _decimal(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> float:
    return float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _effective_tax_rate(net_income: Decimal, employer_total_cost: Decimal) -> float:
    rate = FULL_RATE - (net_income / employer_total_cost)
    return float(rate.quantize(EFFECTIVE_TAX_RATE_QUANT, rounding=ROUND_HALF_UP))
