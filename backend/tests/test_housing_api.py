from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base
from app.models.housing import DistrictRent
from scripts.seed_housing import seed_housing


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with TestingSessionLocal() as session:
        seed_housing(session)
        yield session


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_housing_rents_api_returns_seeded_districts(client: TestClient) -> None:
    response = client.get("/api/v1/housing/rents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city"] == "Tallinn"
    assert payload["updated_at"] == "2026-07-01"
    assert len(payload["districts"]) == 8


def test_housing_rents_api_district_shape_and_values(client: TestClient) -> None:
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


def test_housing_seed_is_idempotent(db_session: Session) -> None:
    seed_housing(db_session)
    seed_housing(db_session)

    districts = db_session.scalars(select(DistrictRent)).all()
    assert len(districts) == 8


def test_housing_rents_api_returns_503_when_database_is_unavailable() -> None:
    class BrokenSession:
        def scalars(self, statement: object) -> object:
            raise SQLAlchemyError("database unavailable")

    def override_get_session() -> Generator[BrokenSession, None, None]:
        yield BrokenSession()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/housing/rents")

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Housing rent data is unavailable"}
