import csv
from pathlib import Path

import pytest

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
    # Manual calculation for 3000 gross, 2% pension:
    # employer social tax = 3000 * 33% = 990.00
    # pension II = 3000 * 2% = 60.00
    # income tax = (3000 - 60 - 700) * 22% = 492.80
    # net = 3000 - 60 - 492.80 = 2447.20
    # employer total cost = 3000 + 990 = 3990.00
    result = calculate_juhatuse_liige(gross_income=3000, pension_pillar_rate=0.02)

    assert result.employer_total_cost == 3990.0
    assert breakdown_amount(result, "income_tax") == 492.8
    assert breakdown_amount(result, "pension_pillar_ii") == 60.0
    assert result.net_income == 2447.2
    assert result.effective_tax_rate == 0.387


def test_juhatuse_liige_below_basic_exemption() -> None:
    # Manual calculation for 500 gross:
    # income tax = max(500 - 700, 0) * 22% = 0.00
    # net = 500 - 0 = 500.00
    result = calculate_juhatuse_liige(gross_income=500, pension_pillar_rate=0.02)

    assert breakdown_amount(result, "income_tax") == 0.0
    assert breakdown_amount(result, "pension_pillar_ii") == 10.0
    assert result.net_income == 490.0


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
    # raw social tax = 500 * 33% = 165.00, so the 292.38 minimum applies.
    # income tax = max(500 - 292.38 - 700, 0) * 22% = 0.00
    # net = 500 - 292.38 - 0 = 207.62
    result = calculate_fie(gross_income=500)

    assert breakdown_amount(result, "social_tax") == 292.38
    assert breakdown_amount(result, "income_tax") == 0.0
    assert result.net_income == 207.62
    assert [constraint.code for constraint in result.constraints] == [
        "fie_social_tax_minimum_applied"
    ]


def test_fie_social_tax_cap() -> None:
    # The 2026 annual cap is 36,867.60, or 3,072.30 in the monthly model.
    # 10,000 * 33% = 3,300, so the cap applies.
    result = calculate_fie(gross_income=10000)

    assert breakdown_amount(result, "social_tax") == 3072.3
    assert result.net_income == 5557.61
    assert [constraint.code for constraint in result.constraints] == [
        "fie_social_tax_cap_applied",
        "vat_registration_threshold_exceeded",
    ]


def test_ettevotluskonto_without_pension_pillar() -> None:
    # Manual calculation for 3000 entrepreneur account receipts:
    # annual receipts = 3000 * 12 = 36000, which is above the old 25000 threshold.
    # EMTA states the 40% business income tax rate no longer applies from 01.01.2025.
    # with 0% pension pillar, business income tax = 3000 * 20% = 600.00
    # net = 3000 - 600 = 2400.00
    result = calculate_ettevotluskonto(gross_income=3000, pension_pillar_rate=0.0)

    assert result.employer_total_cost == 3000.0
    assert breakdown_amount(result, "business_income_tax") == 600.0
    assert result.net_income == 2400.0
    assert result.effective_tax_rate == 0.2


def test_ettevotluskonto_with_default_pension_pillar() -> None:
    # Manual calculation for 3000 entrepreneur account receipts:
    # EMTA 2026 rate for a 2% pension pillar participant = 20% + 2% = 22%.
    # business income tax = 3000 * 22% = 660.00
    # net = 3000 - 660 = 2340.00
    result = calculate_ettevotluskonto(gross_income=3000, pension_pillar_rate=0.02)

    assert breakdown_amount(result, "business_income_tax") == 660.0
    assert result.net_income == 2340.0
    assert result.effective_tax_rate == 0.22


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


def test_compare_regimes_equalizes_payer_cost() -> None:
    response = compare_regimes(
        TaxCalculationRequest(
            gross_monthly_income=3000.0,
            pension_pillar_rate=0.02,
            equalize_by="payer_cost",
        )
    )

    assert all(result.employer_total_cost == 3000.0 for result in response.results)
    assert max(response.results, key=lambda result: result.net_income).regime == "ettevotluskonto"


GOLDEN_FILE = Path(__file__).parent / "data" / "tax_golden.csv"
with GOLDEN_FILE.open(newline="", encoding="utf-8") as golden_file:
    GOLDEN_ROWS = list(csv.DictReader(golden_file))


@pytest.mark.parametrize(
    "row",
    GOLDEN_ROWS,
    ids=lambda row: (
        f"{row['equalize_by']}-{row['gross_monthly_income']}-"
        f"{row['pension_pillar_rate']}-{row['regime']}"
    ),
)
def test_tax_golden_file(row: dict[str, str]) -> None:
    response = compare_regimes(
        TaxCalculationRequest(
            gross_monthly_income=float(row["gross_monthly_income"]),
            pension_pillar_rate=float(row["pension_pillar_rate"]),
            equalize_by=row["equalize_by"],
        )
    )
    result = next(result for result in response.results if result.regime == row["regime"])

    assert result.net_income == pytest.approx(float(row["expected_net_income"]))
    assert result.effective_tax_rate == pytest.approx(
        float(row["expected_effective_tax_rate"])
    )
