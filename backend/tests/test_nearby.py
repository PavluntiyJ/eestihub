"""Nearby platforms, service dates, query bounds and unavailable snapshots."""
from datetime import date, datetime, timezone
from math import degrees

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.db import get_session
from app.models import Base
from app.models.transit import TransitStop
from app.services.nearby_service import EARTH_RADIUS_M, distance_m, get_nearby
from tests.test_transit_import import import_valid

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def test_distance_order_routeless_platforms_and_query_budget(session):
    imported, _ = import_valid(session)
    session.add(TransitStop(feed_id=imported.feed_id, stop_id="empty", stop_name="Alpha",
                           stop_lat=59.437, stop_lon=24.745, location_type="0"))
    session.add(TransitStop(feed_id=imported.feed_id, stop_id="station", stop_name="Station",
                           stop_lat=59.437, stop_lon=24.745, location_type="1"))
    session.commit()
    queries = []
    def record(*args):
        queries.append(args[2])
    event.listen(session.get_bind(), "before_cursor_execute", record)
    try:
        result = get_nearby(session, 59.437, 24.745, now=NOW)
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", record)
    assert len(queries) <= 7
    assert [stop.id for stop in result.stops] == ["00123", "empty", "S2"]
    assert result.stops[1].routes == []
    assert result.stops[0].straight_line_distance_m == 0
    assert [route.id for route in result.stops[0].routes] == ["R1"]
    assert result.feed.freshness == "unknown"
    assert result.feed.data_license == "CC-BY-SA-3.0"


def test_radius_filters_before_rounding_and_limits_result_count(session):
    imported, _ = import_valid(session)
    for name, distance in [("inside", 799.8), ("outside", 800.2)]:
        session.add(TransitStop(feed_id=imported.feed_id, stop_id=name, stop_name=name,
                               stop_lat=59.437 + degrees(distance / EARTH_RADIUS_M), stop_lon=24.745))
    session.commit()
    result = get_nearby(session, 59.437, 24.745, now=NOW)
    assert "inside" in [s.id for s in result.stops]
    assert "outside" not in [s.id for s in result.stops]
    assert next(s for s in result.stops if s.id == "inside").straight_line_distance_m == 800
    for i in range(25):
        session.add(TransitStop(feed_id=imported.feed_id, stop_id=f"near-{i:02d}", stop_name="Same name",
                               stop_lat=59.437, stop_lon=24.745))
    session.commit()
    result = get_nearby(session, 59.437, 24.745, now=NOW)
    assert len(result.stops) == 20
    assert [s.id for s in result.stops] == ["00123"] + [f"near-{i:02d}" for i in range(19)]


def test_tallinn_day_boundary_and_calendar_removal(session):
    import_valid(session)
    # UTC Jan 6, but Jan 7 locally: the fixture removes WD on this day.
    result = get_nearby(session, 59.437, 24.745,
                        now=datetime(2026, 1, 6, 23, 30, tzinfo=timezone.utc))
    assert result.service_date == date(2026, 1, 7)
    assert result.stops[0].routes == []


def test_snapshot_is_not_mixed_with_retained_generation(session):
    import_valid(session)
    imported, _ = import_valid(session, sha="b" * 64,
                              fetched_at=datetime(2026, 9, 23, tzinfo=timezone.utc))
    stop = session.scalar(select(TransitStop).where(TransitStop.feed_id == imported.feed_id,
                                                   TransitStop.stop_id == "00123"))
    stop.stop_name = "Current name"
    session.commit()
    result = get_nearby(session, 59.437, 24.745, now=NOW)
    assert result.stops[0].name == "Current name"
    assert len([s for s in result.stops if s.id == "00123"]) == 1


def test_api_unavailable_empty_and_validation(session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    path = "/api/v1/transit/nearby"
    response = client.get(path, params={"lat": 59.437, "lon": 24.745})
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    import_valid(session)
    response = client.get(path, params={"lat": 59.6, "lon": 24.5})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["stops"] == []
    for params in [{}, {"lat": "nan", "lon": 24.7}, {"lat": 59.4, "lon": "inf"},
                   {"lat": 0, "lon": 24.7}, {"lat": 59.4, "lon": 26}]:
        assert client.get(path, params=params).status_code == 422
    assert distance_m(59.437, 24.745, 59.437, 24.745) == 0
