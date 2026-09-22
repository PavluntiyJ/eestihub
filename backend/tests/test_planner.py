from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.planner import BudgetCalculationRequest
from app.services.tax_service import calculate_tooleping


client = TestClient(app)

ENDPOINT = "/api/v1/planner/budget"


def manual_request(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "income": {"kind": "manual_net", "net_monthly_income": 2400},
        "monthly_non_housing": 700,
        "monthly_savings": 300,
        "housing_share": 0.35,
    }
    payload.update(overrides)
    return payload


def apartment(
    rent: Any = 650,
    summer: Any = 100,
    winter: Any = 200,
    basis: str = "user_estimate",
    move_in: Any = None,
) -> dict[str, Any]:
    return {
        "rent": rent,
        "utilities": {"summer": summer, "winter": winter, "basis": basis},
        "move_in": move_in,
    }


COMPLETE_MOVE_IN = {
    "first_rent": 650,
    "deposit": 650,
    "broker_fee": 0,
    "setup": 200,
}


def test_seasonal_risk_fixture_returns_the_full_contract() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(apartment=apartment(move_in=COMPLETE_MOVE_IN)),
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "schema_version": 1,
        "income": {
            "kind": "manual_net",
            "net_monthly_income": 2400.0,
            "tax_year": None,
        },
        "budget": {
            "monthly_non_housing": 700.0,
            "monthly_savings": 300.0,
            "housing_share": 0.35,
            "available_after_commitments": 1400.0,
            "share_limit": 840.0,
            "housing_allowance": 840.0,
        },
        "apartment": {
            "rent": 650.0,
            "utilities": {"summer": 100.0, "winter": 200.0, "basis": "user_estimate"},
            "summer_total": 750.0,
            "winter_total": 850.0,
            "summer_remainder": 650.0,
            "winter_remainder": 550.0,
            "fit": "seasonal_risk",
            "move_in": {
                "cash_needed": 1500.0,
                "known_subtotal": 1500.0,
                "missing_components": [],
                "refundable_deposit": 650.0,
            },
        },
        "warnings": [],
    }


def test_within_budget_fixture() -> None:
    response = client.post(ENDPOINT, json=manual_request(apartment=apartment(rent=600)))

    assert response.status_code == 200
    body = response.json()
    assert body["apartment"]["summer_remainder"] == 700.0
    assert body["apartment"]["winter_remainder"] == 600.0
    assert body["apartment"]["fit"] == "within_budget"
    assert body["warnings"] == []


def test_over_budget_fixture_keeps_the_signed_deficit() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 1200},
            monthly_non_housing=1000,
            apartment=apartment(rent=600),
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["budget"]["available_after_commitments"] == -100.0
    assert body["budget"]["housing_allowance"] == 0.0
    assert body["apartment"]["summer_remainder"] == -800.0
    assert body["apartment"]["winter_remainder"] == -900.0
    assert body["apartment"]["fit"] == "over_budget"
    assert [warning["code"] for warning in body["warnings"]] == [
        "commitments_exceed_income"
    ]


def test_unknown_utilities_fixture() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(apartment=apartment(summer=None, winter=None, basis="unknown")),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["apartment"]["summer_total"] is None
    assert body["apartment"]["winter_total"] is None
    assert body["apartment"]["summer_remainder"] is None
    assert body["apartment"]["winter_remainder"] is None
    assert body["apartment"]["fit"] == "unknown"
    assert body["apartment"]["utilities"]["summer"] is None
    assert [warning["code"] for warning in body["warnings"]] == ["utilities_incomplete"]


def test_allowance_boundary_counts_as_within_budget() -> None:
    # Remainder-based boundary: allowance comes from income minus commitments.
    remainder_limited = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 2000},
            monthly_non_housing=500,
            monthly_savings=300,
            housing_share=0.5,
            apartment=apartment(rent=900, summer=100, winter=100),
        ),
    )
    # Share-based boundary: allowance comes from the chosen share.
    share_limited = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 2000},
            monthly_non_housing=0,
            monthly_savings=0,
            housing_share=0.5,
            apartment=apartment(rent=900, summer=100, winter=100),
        ),
    )

    assert remainder_limited.status_code == share_limited.status_code == 200
    assert remainder_limited.json()["budget"]["housing_allowance"] == 1000.0
    assert remainder_limited.json()["apartment"]["fit"] == "within_budget"
    assert share_limited.json()["apartment"]["fit"] == "within_budget"


def test_zero_income_and_zero_share_are_valid() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 0},
            monthly_non_housing=0,
            monthly_savings=0,
            housing_share=0,
            apartment=apartment(rent=0, summer=0, winter=0, basis="user_bill"),
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["budget"]["housing_allowance"] == 0.0
    assert body["apartment"]["fit"] == "within_budget"
    assert body["apartment"]["move_in"] is None
    assert body["warnings"] == []


def test_share_limit_rounds_half_up_to_cents() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 1234.56},
            monthly_non_housing=0,
            monthly_savings=0,
            housing_share=0.3333,
        ),
    )

    assert response.status_code == 200
    # 1234.56 * 0.3333 = 411.478288 -> 411.48
    assert response.json()["budget"]["share_limit"] == 411.48
    assert response.json()["budget"]["housing_allowance"] == 411.48


def test_reversed_seasons_use_min_and_max_not_winter() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 2000},
            monthly_non_housing=0,
            monthly_savings=0,
            housing_share=0.5,
            apartment=apartment(rent=850, summer=200, winter=100),
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["apartment"]["fit"] == "seasonal_risk"
    assert body["apartment"]["summer_total"] == 1050.0
    assert body["apartment"]["winter_total"] == 950.0
    assert body["apartment"]["summer_remainder"] == 950.0
    assert body["apartment"]["winter_remainder"] == 1050.0


def test_partial_utilities_stay_unknown() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(apartment=apartment(winter=None)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["apartment"]["summer_total"] == 750.0
    assert body["apartment"]["summer_remainder"] == 650.0
    assert body["apartment"]["winter_total"] is None
    assert body["apartment"]["winter_remainder"] is None
    assert body["apartment"]["fit"] == "unknown"
    assert [warning["code"] for warning in body["warnings"]] == ["utilities_incomplete"]


def test_move_in_unknown_component_returns_the_known_subtotal() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            apartment=apartment(
                move_in={
                    "first_rent": 650,
                    "deposit": None,
                    "broker_fee": 0,
                    "setup": 200,
                }
            )
        ),
    )

    assert response.status_code == 200
    move_in = response.json()["apartment"]["move_in"]
    assert move_in["cash_needed"] is None
    assert move_in["known_subtotal"] == 850.0
    assert move_in["missing_components"] == ["deposit"]
    assert move_in["refundable_deposit"] is None
    assert [warning["code"] for warning in response.json()["warnings"]] == [
        "move_in_incomplete"
    ]


def test_move_in_explicit_zero_is_kept() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            apartment=apartment(
                move_in={"first_rent": 0, "deposit": 0, "broker_fee": 0, "setup": 0}
            )
        ),
    )

    assert response.status_code == 200
    move_in = response.json()["apartment"]["move_in"]
    assert move_in["cash_needed"] == 0.0
    assert move_in["known_subtotal"] == 0.0
    assert move_in["missing_components"] == []
    assert response.json()["warnings"] == []


def test_move_in_null_skips_the_block_without_warning() -> None:
    response = client.post(ENDPOINT, json=manual_request(apartment=apartment()))

    assert response.status_code == 200
    assert response.json()["apartment"]["move_in"] is None
    assert response.json()["warnings"] == []


def test_employment_matches_the_existing_tax_service() -> None:
    response = client.post(
        ENDPOINT,
        json={
            "income": {
                "kind": "employment",
                "gross_monthly_income": 3000,
                "pension_pillar_rate": 0.02,
            },
            "monthly_non_housing": 700,
            "monthly_savings": 300,
            "housing_share": 0.35,
        },
    )

    assert response.status_code == 200
    body = response.json()
    expected_net = calculate_tooleping(3000, 0.02).net_income
    assert body["income"] == {
        "kind": "employment",
        "net_monthly_income": expected_net,
        "tax_year": 2026,
    }
    assert expected_net == 2409.76
    assert body["budget"]["available_after_commitments"] == 1409.76
    assert body["budget"]["housing_allowance"] == 843.42


def test_apartment_absent_returns_null_and_no_warnings() -> None:
    response = client.post(ENDPOINT, json=manual_request())

    assert response.status_code == 200
    assert response.json()["apartment"] is None
    assert response.json()["warnings"] == []


def test_warning_order_is_deterministic() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            income={"kind": "manual_net", "net_monthly_income": 1200},
            monthly_non_housing=1000,
            apartment=apartment(
                rent=600,
                summer=None,
                winter=None,
                basis="unknown",
                move_in={
                    "first_rent": 100,
                    "deposit": None,
                    "broker_fee": None,
                    "setup": None,
                },
            ),
        ),
    )

    assert response.status_code == 200
    assert [warning["code"] for warning in response.json()["warnings"]] == [
        "commitments_exceed_income",
        "utilities_incomplete",
        "move_in_incomplete",
    ]


def test_response_values_are_json_numbers_not_strings() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(apartment=apartment(move_in=COMPLETE_MOVE_IN)),
    )

    body = response.json()
    values = [
        body["income"]["net_monthly_income"],
        body["budget"]["available_after_commitments"],
        body["budget"]["share_limit"],
        body["budget"]["housing_allowance"],
        body["apartment"]["rent"],
        body["apartment"]["summer_total"],
        body["apartment"]["summer_remainder"],
        body["apartment"]["move_in"]["cash_needed"],
    ]

    for value in values:
        assert isinstance(value, (int, float))
        assert not isinstance(value, bool)


@pytest.mark.parametrize(
    "payload",
    [
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": 0,
                "pension_pillar_rate": 0.02,
            }
        ),
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": 1000000.01,
                "pension_pillar_rate": 0.02,
            }
        ),
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": 3000.123,
                "pension_pillar_rate": 0.02,
            }
        ),
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": 3000,
                "pension_pillar_rate": 0.03,
            }
        ),
        manual_request(
            income={"kind": "employment", "gross_monthly_income": 3000}
        ),
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": 3000,
                "pension_pillar_rate": 0.02,
                "net_monthly_income": 2400,
            }
        ),
        manual_request(income={"kind": "contractor", "gross_monthly_income": 3000}),
        manual_request(monthly_non_housing=-1),
        manual_request(monthly_savings=1.234),
        manual_request(housing_share=1.5),
        manual_request(housing_share=0.12345),
        # JSON booleans are not money: bool subclasses int, so without an
        # explicit guard True/False would silently become 1/0 amounts.
        manual_request(income={"kind": "manual_net", "net_monthly_income": True}),
        manual_request(income={"kind": "manual_net", "net_monthly_income": False}),
        manual_request(monthly_non_housing=True),
        manual_request(housing_share=True),
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": True,
                "pension_pillar_rate": 0.02,
            }
        ),
        manual_request(
            income={
                "kind": "employment",
                "gross_monthly_income": 3000,
                "pension_pillar_rate": False,
            }
        ),
        # Strict-JSON-reachable non-finite and non-numeric amounts.
        manual_request(income={"kind": "manual_net", "net_monthly_income": "NaN"}),
        manual_request(
            income={"kind": "manual_net", "net_monthly_income": "Infinity"}
        ),
        manual_request(income={"kind": "manual_net", "net_monthly_income": "abc"}),
        manual_request(extra_field=True),
        manual_request(apartment={"rent": 650, "move_in": None}),
        manual_request(
            apartment=apartment(summer=100, winter=None, basis="unknown")
        ),
        manual_request(apartment=apartment(summer=None, winter=None, basis="user_bill")),
        manual_request(apartment={"rent": 650, "utilities": {
            "summer": 100, "winter": 200, "basis": "user_estimate"
        }}),
        # Required nullable keys: omitted seasonal amounts and move-in
        # components are 422, explicit null stays valid (see the
        # explicit-null success tests).
        manual_request(
            apartment={"rent": 650, "utilities": {"basis": "unknown"}, "move_in": None}
        ),
        manual_request(
            apartment={
                "rent": 650,
                "utilities": {"summer": 100, "basis": "user_estimate"},
                "move_in": None,
            }
        ),
        manual_request(apartment=apartment(move_in={})),
        manual_request(apartment=apartment(move_in={"first_rent": 650})),
    ],
)
def test_invalid_requests_return_422(payload: dict[str, Any]) -> None:
    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("raw_value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_literals_return_json_safe_422(raw_value: str) -> None:
    # Non-strict JSON literals reach the route as non-finite floats. The
    # validation error echoes them, so the 422 envelope itself must stay
    # JSON-serializable instead of becoming a 500. The shared TestClient
    # raises server exceptions, so any 500 would fail loudly here.
    raw = (
        '{"income":{"kind":"manual_net","net_monthly_income":'
        + raw_value
        + '},"monthly_non_housing":700,"monthly_savings":300,"housing_share":0.35}'
    )
    response = client.post(
        ENDPOINT, content=raw.encode(), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "net_monthly_income"


def test_exponent_overflow_returns_json_safe_422() -> None:
    # 1e400 is valid JSON number syntax but overflows float decoding to
    # Infinity; the 422 envelope must still serialize as JSON.
    raw = (
        b'{"income":{"kind":"manual_net","net_monthly_income":1e400},'
        b'"monthly_non_housing":700,"monthly_savings":300,"housing_share":0.35}'
    )
    response = client.post(
        ENDPOINT, content=raw, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "net_monthly_income"


def test_move_in_all_null_is_valid_with_zero_known_subtotal() -> None:
    response = client.post(
        ENDPOINT,
        json=manual_request(
            apartment=apartment(
                move_in={
                    "first_rent": None,
                    "deposit": None,
                    "broker_fee": None,
                    "setup": None,
                }
            )
        ),
    )

    assert response.status_code == 200
    move_in = response.json()["apartment"]["move_in"]
    assert move_in["cash_needed"] is None
    assert move_in["known_subtotal"] == 0.0
    assert move_in["missing_components"] == [
        "first_rent",
        "deposit",
        "broker_fee",
        "setup",
    ]
    assert move_in["refundable_deposit"] is None
    assert [warning["code"] for warning in response.json()["warnings"]] == [
        "move_in_incomplete"
    ]


def test_schema_rejects_non_finite_values() -> None:
    # Strict JSON has no NaN or Infinity. The schema still refuses them so a
    # non-strict client cannot smuggle a non-finite amount into the maths; the
    # HTTP path for such a body is recorded in the M05 journal notes.
    with pytest.raises(ValidationError):
        BudgetCalculationRequest.model_validate(
            manual_request(
                income={"kind": "manual_net", "net_monthly_income": float("nan")}
            )
        )
