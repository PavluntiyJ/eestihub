from app.schemas.taxes import TaxCalculationRequest
from app.services.tax_service import (
    calculate_ettevotluskonto,
    calculate_fie,
    calculate_juhatuse_liige,
    calculate_tooleping,
    compare_regimes,
)


def breakdown_amount(result, name: str) -> float:
    return next(line.amount for line in result.breakdown if line.name == name)


def test_tooleping_with_default_pension_rate() -> None:
    # Manual calculation for 3000 gross, 2% pension:
    # employer social tax = 3000 * 33% = 990.00
    # employer unemployment = 3000 * 0.8% = 24.00
    # employee unemployment = 3000 * 1.6% = 48.00
    # pension II = 3000 * 2% = 60.00
    # income tax = (3000 - 48 - 60 - 700) * 22% = 482.24
    # net = 3000 - 48 - 60 - 482.24 = 2409.76
    # employer total cost = 3000 + 990 + 24 = 4014.00
    result = calculate_tooleping(gross_income=3000, pension_pillar_rate=0.02)

    assert result.employer_total_cost == 4014.0
    assert breakdown_amount(result, "income_tax") == 482.24
    assert breakdown_amount(result, "unemployment_insurance_employee") == 48.0
    assert breakdown_amount(result, "pension_pillar_ii") == 60.0
    assert result.net_income == 2409.76
    assert result.effective_tax_rate == 0.4


def test_tooleping_with_zero_pension_rate() -> None:
    # Manual calculation for 3000 gross, 0% pension:
    # employee unemployment = 3000 * 1.6% = 48.00
    # pension II = 3000 * 0% = 0.00
    # income tax = (3000 - 48 - 0 - 700) * 22% = 495.44
    # net = 3000 - 48 - 0 - 495.44 = 2456.56
    result = calculate_tooleping(gross_income=3000, pension_pillar_rate=0.0)

    assert breakdown_amount(result, "income_tax") == 495.44
    assert breakdown_amount(result, "pension_pillar_ii") == 0.0
    assert result.net_income == 2456.56


def test_juhatuse_liige() -> None:
    # Manual calculation for 3000 gross:
    # employer social tax = 3000 * 33% = 990.00
    # income tax = (3000 - 700) * 22% = 506.00
    # net = 3000 - 506 = 2494.00
    # employer total cost = 3000 + 990 = 3990.00
    result = calculate_juhatuse_liige(gross_income=3000)

    assert result.employer_total_cost == 3990.0
    assert breakdown_amount(result, "income_tax") == 506.0
    assert result.net_income == 2494.0
    assert result.effective_tax_rate == 0.375


def test_juhatuse_liige_below_basic_exemption() -> None:
    # Manual calculation for 500 gross:
    # income tax = max(500 - 700, 0) * 22% = 0.00
    # net = 500 - 0 = 500.00
    result = calculate_juhatuse_liige(gross_income=500)

    assert breakdown_amount(result, "income_tax") == 0.0
    assert result.net_income == 500.0


def test_fie() -> None:
    # Manual calculation for 3000 business income:
    # social tax = 3000 * 33% = 990.00
    # income tax = (3000 - 990 - 700) * 22% = 288.20
    # net = 3000 - 990 - 288.20 = 1721.80
    result = calculate_fie(gross_income=3000)

    assert result.employer_total_cost == 3000.0
    assert breakdown_amount(result, "social_tax") == 990.0
    assert breakdown_amount(result, "income_tax") == 288.2
    assert result.net_income == 1721.8
    assert result.effective_tax_rate == 0.426


def test_fie_below_basic_exemption_after_social_tax() -> None:
    # Manual calculation for 500 business income:
    # social tax = 500 * 33% = 165.00
    # income tax = max(500 - 165 - 700, 0) * 22% = 0.00
    # net = 500 - 165 - 0 = 335.00
    result = calculate_fie(gross_income=500)

    assert breakdown_amount(result, "social_tax") == 165.0
    assert breakdown_amount(result, "income_tax") == 0.0
    assert result.net_income == 335.0


def test_ettevotluskonto_current_2026_rate() -> None:
    # Manual calculation for 3000 entrepreneur account receipts:
    # annual receipts = 3000 * 12 = 36000, which is above the old 25000 threshold.
    # EMTA states the 40% business income tax rate no longer applies from 01.01.2025.
    # business income tax = 3000 * 20% = 600.00
    # net = 3000 - 600 = 2400.00
    result = calculate_ettevotluskonto(gross_income=3000)

    assert result.employer_total_cost == 3000.0
    assert breakdown_amount(result, "business_income_tax") == 600.0
    assert result.net_income == 2400.0
    assert result.effective_tax_rate == 0.2


def test_ettevotluskonto_small_receipts() -> None:
    # Manual calculation for 1000 entrepreneur account receipts:
    # business income tax = 1000 * 20% = 200.00
    # net = 1000 - 200 = 800.00
    result = calculate_ettevotluskonto(gross_income=1000)

    assert breakdown_amount(result, "business_income_tax") == 200.0
    assert result.net_income == 800.0


def test_compare_regimes_returns_all_four_regimes() -> None:
    # Manual coverage check: one input should produce one result for each MVP regime.
    response = compare_regimes(
        TaxCalculationRequest(gross_monthly_income=3000.0, pension_pillar_rate=0.02)
    )

    assert [result.regime for result in response.results] == [
        "tooleping",
        "juhatuse_liige",
        "fie",
        "ettevotluskonto",
    ]
