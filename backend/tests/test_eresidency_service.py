from app.schemas.eresidency import EResidencyCalculationRequest
from app.services.eresidency_service import calculate_eresidency_costs


def test_calculate_eresidency_costs_with_default_accounting() -> None:
    # Manual derivation:
    # setup = 150 application + 265 OÜ registration + 300 contact person = 715
    # accounting = 75 * 12 = 900
    # first-year cost = 715 + 900 = 1,615
    # break-even revenue = 1,615 / 12 = 134.583..., rounded half-up = 135
    # revenue = 3,000 * 12 = 36,000; surplus = 36,000 - 1,615 = 34,385
    result = calculate_eresidency_costs(
        EResidencyCalculationRequest(expected_monthly_revenue=3000)
    )

    assert result.input.monthly_accounting_fee == 75.0
    assert [(line.name, line.amount) for line in result.setup_breakdown] == [
        ("eresidency_application", 150.0),
        ("ou_online_registration", 265.0),
        ("contact_person_first_year", 300.0),
    ]
    assert result.monthly_running_cost == 75.0
    assert result.first_year_total_cost == 1615.0
    assert result.break_even_monthly_revenue == 135.0
    assert result.first_year_revenue == 36000.0
    assert result.first_year_surplus == 34385.0


def test_calculate_eresidency_costs_with_custom_accounting() -> None:
    # Manual derivation with no outsourced monthly accounting:
    # first-year cost = 715 + (0 * 12) = 715
    # break-even revenue = 715 / 12 = 59.583..., rounded half-up = 60
    # revenue = 50 * 12 = 600; surplus = 600 - 715 = -115
    result = calculate_eresidency_costs(
        EResidencyCalculationRequest(
            expected_monthly_revenue=50,
            monthly_accounting_fee=0,
        )
    )

    assert result.monthly_running_cost == 0.0
    assert result.first_year_total_cost == 715.0
    assert result.break_even_monthly_revenue == 60.0
    assert result.first_year_revenue == 600.0
    assert result.first_year_surplus == -115.0
