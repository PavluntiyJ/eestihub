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
    assert payload["input"] == {
        "gross_monthly_income": 3000.0,
        "pension_pillar_rate": 0.02,
        "equalize_by": "gross",
    }
    assert len(payload["results"]) == 4

    by_regime = {result["regime"]: result for result in payload["results"]}
    assert by_regime["tooleping"]["net_income"] == 2409.76
    assert by_regime["tooleping"]["employer_total_cost"] == 4014.0
    assert by_regime["juhatuse_liige"]["net_income"] == 2447.2
    assert {line["name"] for line in by_regime["juhatuse_liige"]["breakdown"]} == {
        "income_tax",
        "pension_pillar_ii",
    }
    assert by_regime["ettevotluskonto"]["net_income"] == 2340.0
    assert all("constraints" in result for result in payload["results"])


def test_calculate_taxes_api_equalizes_payer_cost() -> None:
    response = client.post(
        "/api/v1/calculate-taxes",
        json={
            "gross_monthly_income": 3000.0,
            "pension_pillar_rate": 0.02,
            "equalize_by": "payer_cost",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert all(result["employer_total_cost"] == 3000.0 for result in payload["results"])
    assert max(payload["results"], key=lambda result: result["net_income"])["regime"] == (
        "ettevotluskonto"
    )


def test_calculate_taxes_api_surfaces_statutory_constraints() -> None:
    high_income = client.post(
        "/api/v1/calculate-taxes", json={"gross_monthly_income": 5000.0}
    )
    low_income = client.post(
        "/api/v1/calculate-taxes", json={"gross_monthly_income": 500.0}
    )

    high_results = {
        result["regime"]: result for result in high_income.json()["results"]
    }
    low_results = {result["regime"]: result for result in low_income.json()["results"]}
    assert {
        "code": "ettevotluskonto_annual_limit_exceeded",
        "severity": "blocker",
    } in high_results["ettevotluskonto"]["constraints"]
    assert {
        "code": "fie_social_tax_minimum_applied",
        "severity": "info",
    } in low_results["fie"]["constraints"]


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
