from decimal import Decimal, ROUND_HALF_UP

from app.core.tax_rates import (
    BASIC_EXEMPTION_MONTHLY,
    EFFECTIVE_TAX_RATE_QUANT,
    ENTREPRENEUR_ACCOUNT_MONTHLY_LIMIT,
    ENTREPRENEUR_ACCOUNT_TAX_RATE,
    FIE_SOCIAL_TAX_MINIMUM_MONTHLY,
    FIE_SOCIAL_TAX_MONTHLY_MAXIMUM,
    INCOME_TAX_RATE,
    MONEY_QUANT,
    SOCIAL_TAX_RATE,
    UNEMPLOYMENT_INSURANCE_EMPLOYEE_RATE,
    UNEMPLOYMENT_INSURANCE_EMPLOYER_RATE,
    VAT_REGISTRATION_MONTHLY_THRESHOLD,
)
from app.schemas.taxes import (
    Constraint,
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


def calculate_juhatuse_liige(
    gross_income: Decimal | float | int, pension_pillar_rate: Decimal | float | int
) -> RegimeResult:
    gross_income = _decimal(gross_income)
    pension_pillar_rate = _decimal(pension_pillar_rate)

    employer_social_tax = gross_income * SOCIAL_TAX_RATE
    pension_pillar = gross_income * pension_pillar_rate
    income_tax = _income_tax(gross_income - pension_pillar)
    employer_total_cost = gross_income + employer_social_tax
    net_income = gross_income - pension_pillar - income_tax

    return _result(
        regime="juhatuse_liige",
        label="Management board member (Juhatuse liige)",
        employer_total_cost=employer_total_cost,
        gross_income=gross_income,
        breakdown=[
            TaxLine(name="income_tax", amount=_money(income_tax)),
            TaxLine(name="pension_pillar_ii", amount=_money(pension_pillar)),
        ],
        net_income=net_income,
    )


def calculate_fie(gross_income: Decimal | float | int) -> RegimeResult:
    gross_income = _decimal(gross_income)

    unconstrained_social_tax = gross_income * SOCIAL_TAX_RATE
    social_tax = min(
        max(unconstrained_social_tax, FIE_SOCIAL_TAX_MINIMUM_MONTHLY),
        FIE_SOCIAL_TAX_MONTHLY_MAXIMUM,
    )
    constraints: list[Constraint] = []
    if unconstrained_social_tax < FIE_SOCIAL_TAX_MINIMUM_MONTHLY:
        constraints.append(
            Constraint(code="fie_social_tax_minimum_applied", severity="info")
        )
    elif unconstrained_social_tax > FIE_SOCIAL_TAX_MONTHLY_MAXIMUM:
        constraints.append(Constraint(code="fie_social_tax_cap_applied", severity="info"))
    if gross_income > VAT_REGISTRATION_MONTHLY_THRESHOLD:
        constraints.append(
            Constraint(code="vat_registration_threshold_exceeded", severity="warning")
        )
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
        constraints=constraints,
    )


def calculate_ettevotluskonto(
    gross_income: Decimal | float | int, pension_pillar_rate: Decimal | float | int
) -> RegimeResult:
    gross_income = _decimal(gross_income)
    pension_pillar_rate = _decimal(pension_pillar_rate)

    business_income_tax = gross_income * (ENTREPRENEUR_ACCOUNT_TAX_RATE + pension_pillar_rate)
    net_income = gross_income - business_income_tax
    constraints: list[Constraint] = []
    if gross_income > ENTREPRENEUR_ACCOUNT_MONTHLY_LIMIT:
        constraints.append(
            Constraint(code="ettevotluskonto_annual_limit_exceeded", severity="blocker")
        )
    if gross_income > VAT_REGISTRATION_MONTHLY_THRESHOLD:
        constraints.append(
            Constraint(code="vat_registration_threshold_exceeded", severity="warning")
        )

    return _result(
        regime="ettevotluskonto",
        label="Entrepreneur account (Ettevõtluskonto)",
        employer_total_cost=gross_income,
        gross_income=gross_income,
        breakdown=[TaxLine(name="business_income_tax", amount=_money(business_income_tax))],
        net_income=net_income,
        constraints=constraints,
    )


def compare_regimes(request: TaxCalculationRequest) -> TaxCalculationResponse:
    input_amount = _decimal(request.gross_monthly_income)
    pension_pillar_rate = _decimal(request.pension_pillar_rate)
    if request.equalize_by == "payer_cost":
        tooleping_gross = input_amount / (
            Decimal("1") + SOCIAL_TAX_RATE + UNEMPLOYMENT_INSURANCE_EMPLOYER_RATE
        )
        juhatuse_liige_gross = input_amount / (Decimal("1") + SOCIAL_TAX_RATE)
    else:
        tooleping_gross = input_amount
        juhatuse_liige_gross = input_amount

    return TaxCalculationResponse(
        input=request,
        results=[
            calculate_tooleping(tooleping_gross, pension_pillar_rate),
            calculate_juhatuse_liige(juhatuse_liige_gross, pension_pillar_rate),
            calculate_fie(input_amount),
            calculate_ettevotluskonto(input_amount, pension_pillar_rate),
        ],
    )


def _income_tax(income_before_basic_exemption: Decimal) -> Decimal:
    taxable_income = max(
        income_before_basic_exemption - BASIC_EXEMPTION_MONTHLY,
        Decimal("0"),
    )
    return taxable_income * INCOME_TAX_RATE


def _result(
    regime: str,
    label: str,
    employer_total_cost: Decimal,
    gross_income: Decimal,
    breakdown: list[TaxLine],
    net_income: Decimal,
    constraints: list[Constraint] | None = None,
) -> RegimeResult:
    return RegimeResult(
        regime=regime,
        label=label,
        employer_total_cost=_money(employer_total_cost),
        gross_income=_money(gross_income),
        breakdown=breakdown,
        net_income=_money(net_income),
        effective_tax_rate=_effective_tax_rate(net_income, employer_total_cost),
        constraints=constraints or [],
    )


def _decimal(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> float:
    return float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _effective_tax_rate(net_income: Decimal, employer_total_cost: Decimal) -> float:
    rate = Decimal("1") - (net_income / employer_total_cost)
    return float(rate.quantize(EFFECTIVE_TAX_RATE_QUANT, rounding=ROUND_HALF_UP))
