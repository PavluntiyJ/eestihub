from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_housing_rents_api_returns_mock_districts() -> None:
    response = client.get("/api/v1/housing/rents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city"] == "Tallinn"
    assert payload["updated_at"] == "2026-07-01"
    assert len(payload["districts"]) == 8


def test_housing_rents_api_district_shape_and_values() -> None:
    response = client.get("/api/v1/housing/rents")

    assert response.status_code == 200
    payload = response.json()
    required_fields = {
        "name",
        "avg_rent_1room",
        "avg_rent_2room",
        "avg_rent_3room",
        "avg_utilities",
        "lat",
        "lon",
    }

    for district in payload["districts"]:
        assert required_fields == set(district)
        assert district["avg_rent_1room"] > 0
        assert district["avg_rent_2room"] > 0
        assert district["avg_rent_3room"] > 0
        assert district["avg_utilities"] > 0
        assert district["avg_rent_1room"] < district["avg_rent_3room"]
