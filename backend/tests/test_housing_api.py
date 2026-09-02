from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base
from app.models.housing import DistrictRent, RentSnapshot
from scripts.ingest_rents import ingest_rents
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
    assert [district["name"] for district in payload["districts"]] == sorted(
        district["name"] for district in payload["districts"]
    )


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


def test_housing_rents_prefers_latest_snapshot_per_district(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all(
        [
            RentSnapshot(
                city="Tallinn",
                district_name="Kesklinn",
                captured_on=date(2026, 8, 1),
                avg_rent_1room=700,
                avg_rent_2room=900,
                avg_rent_3room=1200,
                avg_utilities=None,
                source="https://example.com/older",
            ),
            RentSnapshot(
                city="Tallinn",
                district_name="Kesklinn",
                captured_on=date(2026, 9, 1),
                avg_rent_1room=800,
                avg_rent_2room=1000,
                avg_rent_3room=1300,
                avg_utilities=210,
                source="https://example.com/latest",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/housing/rents")

    assert response.status_code == 200
    payload = response.json()
    by_name = {district["name"]: district for district in payload["districts"]}
    assert payload["updated_at"] == "2026-09-01"
    assert by_name["Kesklinn"]["avg_rent_1room"] == 800
    assert by_name["Kesklinn"]["avg_utilities"] == 210
    assert by_name["Lasnamäe"]["avg_rent_1room"] == 430


def test_housing_rents_keeps_legacy_utilities_when_snapshot_omits_them(
    client: TestClient, db_session: Session
) -> None:
    db_session.add(
        RentSnapshot(
            city="Tallinn",
            district_name="Kesklinn",
            captured_on=date(2026, 9, 1),
            avg_rent_1room=800,
            avg_rent_2room=1000,
            avg_rent_3room=1300,
            avg_utilities=None,
            source="https://example.com/latest",
        )
    )
    db_session.commit()

    response = client.get("/api/v1/housing/rents")

    kesklinn = next(
        district
        for district in response.json()["districts"]
        if district["name"] == "Kesklinn"
    )
    assert response.status_code == 200
    assert kesklinn["avg_utilities"] == 210


def test_rent_snapshot_ingest_is_idempotent(db_session: Session) -> None:
    ingest_rents(db_session)
    ingest_rents(db_session)

    snapshot_count = db_session.scalar(select(func.count()).select_from(RentSnapshot))
    kesklinn = db_session.scalar(
        select(RentSnapshot).where(RentSnapshot.district_name == "Kesklinn")
    )
    assert snapshot_count == 8
    assert kesklinn is not None
    assert kesklinn.captured_on == date(2026, 5, 27)
    assert kesklinn.avg_rent_2room == 1125
    assert kesklinn.avg_utilities is None


def test_housing_rents_api_uses_ingested_snapshot(
    client: TestClient, db_session: Session
) -> None:
    ingest_rents(db_session)

    response = client.get("/api/v1/housing/rents")

    assert response.status_code == 200
    payload = response.json()
    by_name = {district["name"]: district for district in payload["districts"]}
    assert payload["updated_at"] == "2026-05-27"
    assert by_name["Kesklinn"]["avg_rent_2room"] == 1125
    assert by_name["Kesklinn"]["avg_utilities"] == 210


def test_housing_trends_api_returns_ordered_series(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all(
        [
            RentSnapshot(
                city="Tallinn",
                district_name="Kesklinn",
                captured_on=date(2026, 9, 1),
                avg_rent_1room=800,
                avg_rent_2room=1000,
                avg_rent_3room=1300,
                avg_utilities=None,
                source="https://example.com/latest",
            ),
            RentSnapshot(
                city="Tallinn",
                district_name="Kesklinn",
                captured_on=date(2026, 8, 1),
                avg_rent_1room=700,
                avg_rent_2room=900,
                avg_rent_3room=1200,
                avg_utilities=190,
                source="https://example.com/older",
            ),
            RentSnapshot(
                city="Tallinn",
                district_name="Lasnamäe",
                captured_on=date(2026, 8, 1),
                avg_rent_1room=500,
                avg_rent_2room=650,
                avg_rent_3room=850,
                avg_utilities=170,
                source="https://example.com/older",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/housing/trends")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city"] == "Tallinn"
    assert [district["name"] for district in payload["districts"]] == [
        "Kesklinn",
        "Lasnamäe",
    ]
    assert [
        point["captured_on"] for point in payload["districts"][0]["points"]
    ] == ["2026-08-01", "2026-09-01"]
    assert set(payload["districts"][0]["points"][0]) == {
        "captured_on",
        "avg_rent_1room",
        "avg_rent_2room",
        "avg_rent_3room",
        "avg_utilities",
        "source",
    }


def test_housing_trends_api_returns_503_without_snapshots(client: TestClient) -> None:
    response = client.get("/api/v1/housing/trends")

    assert response.status_code == 503
    assert response.json() == {"detail": "Housing rent trend data is unavailable"}


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


def test_housing_trends_api_returns_503_when_database_is_unavailable() -> None:
    class BrokenSession:
        def scalars(self, statement: object) -> object:
            raise SQLAlchemyError("database unavailable")

    def override_get_session() -> Generator[BrokenSession, None, None]:
        yield BrokenSession()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/housing/trends")

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Housing rent trend data is unavailable"}
