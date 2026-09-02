from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import get_session
from app.main import app


class HealthySession:
    def execute(self, statement: object) -> None:
        return None


class UnavailableSession:
    def execute(self, statement: object) -> None:
        raise SQLAlchemyError("database unavailable")


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[HealthySession, None, None]:
        yield HealthySession()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unavailable(client: TestClient) -> None:
    def override_get_session() -> Generator[UnavailableSession, None, None]:
        yield UnavailableSession()

    app.dependency_overrides[get_session] = override_get_session

    health_response = client.get("/api/v1/health")
    taxes_response = client.post(
        "/api/v1/calculate-taxes",
        json={"gross_monthly_income": 3000, "pension_pillar_rate": 0.02},
    )

    assert health_response.status_code == 503
    assert health_response.json() == {
        "status": "degraded",
        "database": "unavailable",
    }
    assert taxes_response.status_code == 200
