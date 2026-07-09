from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_calculate_taxes_api_returns_four_results() -> None:
    # Manual calculation spot-check for the request from CONTEXT.md:
    # Tööleping net = 3000 - (3000 * 1.6%) - (3000 * 2%)
    # - ((3000 - 48 - 60 - 700) * 22%) = 2409.76.
    response = client.post(
        "/api/v1/calculate-taxes",
        json={"gross_monthly_income": 3000.0, "pension_pillar_rate": 0.02},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input"] == {"gross_monthly_income": 3000.0, "pension_pillar_rate": 0.02}
    assert len(payload["results"]) == 4

    by_regime = {result["regime"]: result for result in payload["results"]}
    assert by_regime["tooleping"]["net_income"] == 2409.76
    assert by_regime["tooleping"]["employer_total_cost"] == 4014.0
    assert by_regime["ettevotluskonto"]["net_income"] == 2340.0


def test_calculate_taxes_api_rejects_negative_income() -> None:
    # Manual validation check: negative gross income violates gross_monthly_income > 0.
    response = client.post(
        "/api/v1/calculate-taxes",
        json={"gross_monthly_income": -1.0, "pension_pillar_rate": 0.02},
    )

    assert response.status_code == 422


def test_calculate_taxes_api_rejects_unsupported_pension_rate() -> None:
    # Manual validation check: 3% is outside the allowed 0%, 2%, 4%, 6% set.
    response = client.post(
        "/api/v1/calculate-taxes",
        json={"gross_monthly_income": 3000.0, "pension_pillar_rate": 0.03},
    )

    assert response.status_code == 422
