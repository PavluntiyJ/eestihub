from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_calculate_eresidency_api_returns_complete_estimate() -> None:
    response = client.post(
        "/api/v1/calculate-eresidency",
        json={"expected_monthly_revenue": 3000.0},
    )

    assert response.status_code == 200
    assert response.json() == {
        "input": {
            "expected_monthly_revenue": 3000.0,
            "monthly_accounting_fee": 75.0,
        },
        "setup_breakdown": [
            {"name": "eresidency_application", "amount": 150.0},
            {"name": "ou_online_registration", "amount": 265.0},
            {"name": "contact_person_first_year", "amount": 300.0},
        ],
        "monthly_running_cost": 75.0,
        "first_year_total_cost": 1615.0,
        "break_even_monthly_revenue": 135.0,
        "first_year_revenue": 36000.0,
        "first_year_surplus": 34385.0,
    }


def test_calculate_eresidency_api_accepts_custom_accounting_fee() -> None:
    response = client.post(
        "/api/v1/calculate-eresidency",
        json={
            "expected_monthly_revenue": 1000.0,
            "monthly_accounting_fee": 120.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["monthly_running_cost"] == 120.0
    assert response.json()["first_year_total_cost"] == 2155.0


def test_calculate_eresidency_api_rejects_invalid_inputs() -> None:
    invalid_revenue = client.post(
        "/api/v1/calculate-eresidency",
        json={"expected_monthly_revenue": 0},
    )
    invalid_accounting = client.post(
        "/api/v1/calculate-eresidency",
        json={
            "expected_monthly_revenue": 1000,
            "monthly_accounting_fee": -1,
        },
    )

    assert invalid_revenue.status_code == 422
    assert invalid_accounting.status_code == 422
