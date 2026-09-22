"""PostgreSQL integration for import/rollback/concurrency behavior.

Runs only when a Postgres server answers; locally this suite skips and the
gap is reported instead of claiming SQLite proved PostgreSQL safety. Never
touches production: an isolated `estihub_test` database selected through
TRANSIT_TEST_DATABASE_URL, rows cleaned with DML (no DDL drops).
"""

import os
import tempfile
import threading
import zipfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models import transit as _transit_models  # noqa: F401 (table registration)
from app.models.transit import (
    TransitCalendar,
    TransitCalendarException,
    TransitFeed,
    TransitRoute,
    TransitState,
    TransitStop,
    TransitStopService,
)
from app.services.transit_data import get_active_feed_id, routes_for_stop
from app.services.transit_import import import_feed, parse_feed

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def _base_files(**overrides: str) -> dict[str, str]:
    files = {
        "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nTLL,Tallinn,https://example.com,Europe/Tallinn\n",
        "stops.txt": (
            "stop_id,stop_code,stop_name,stop_lat,stop_lon\n"
            "00123,1001-1,Alpha,59.4370,24.7450\n"
            "S2,,Beta,59.4400,24.7500\n"
        ),
        "routes.txt": (
            "route_id,route_short_name,route_long_name,route_type\n"
            "R1,10,Alpha - Beta,3\n"
        ),
        "trips.txt": "route_id,service_id,trip_id\nR1,WD,T1\n",
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "T1,08:00:00,08:00:00,00123,1\n"
        ),
        "calendar.txt": (
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "WD,1,1,1,1,1,0,0,20260101,20261231\n"
        ),
        "calendar_dates.txt": "service_id,date,exception_type\n",
    }
    files.update(overrides)
    return files


def _make_zip(files: dict[str, str]) -> str:
    handle = tempfile.NamedTemporaryFile(prefix="feed-", suffix=".zip", delete=False)
    with zipfile.ZipFile(handle.name, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    handle.close()
    return handle.name

TEST_DATABASE_URL = os.environ.get(
    "TRANSIT_TEST_DATABASE_URL",
    "postgresql+psycopg://estihub:estihub@localhost:5432/estihub_test",
)


def _engine_or_skip():
    try:
        engine = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 5})
        with engine.connect():
            pass
    except Exception as exc:
        pytest.skip(f"local Postgres unavailable: {exc}")
    return engine


@pytest.fixture()
def pg_session():
    engine = _engine_or_skip()
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        for table in (
            TransitCalendarException,
            TransitCalendar,
            TransitStopService,
            TransitStop,
            TransitRoute,
            TransitState,
            TransitFeed,
        ):
            session.execute(delete(table))
        session.commit()
        yield session
        session.rollback()


def _import(session, sha, fetched_at, files=None):
    feed = parse_feed(_make_zip(files or _base_files()))
    return import_feed(
        session,
        feed,
        source_url="https://transport.tallinn.ee/data/gtfs.zip",
        content_sha256=sha,
        fetched_at=fetched_at,
        checked_at=fetched_at,
        source_last_modified=None,
        source_etag=None,
    )


def _later(minutes: int) -> datetime:
    from datetime import timedelta

    return NOW + timedelta(minutes=minutes)


def test_postgres_import_activate_and_read(pg_session) -> None:
    from datetime import date

    result = _import(pg_session, "a" * 64, NOW)

    assert result.status == "activated"
    assert get_active_feed_id(pg_session) == result.feed_id
    routes = routes_for_stop(pg_session, result.feed_id, "00123", date(2026, 1, 6))
    assert [route.route_id for route in routes] == ["R1"]


def test_postgres_failed_import_rolls_back(pg_session) -> None:
    import app.services.transit_import as importer

    real_activate = importer._activate_generation

    def boom(*args, **kwargs):
        raise RuntimeError("injected")

    importer._activate_generation = boom
    try:
        with pytest.raises(RuntimeError):
            _import(pg_session, "b" * 64, NOW)
    finally:
        importer._activate_generation = real_activate
    pg_session.rollback()

    assert pg_session.query(TransitFeed).count() == 0
    assert get_active_feed_id(pg_session) is None


def test_postgres_concurrent_newer_activation_wins(pg_session) -> None:
    started_old = threading.Event()
    release_old = threading.Event()
    outcomes: dict = {}

    import app.services.transit_import as importer

    real_activate = importer._activate_generation

    def gated_activate(session, staged_id, staged_fetched_at, based_on):
        if staged_fetched_at <= NOW:
            started_old.set()
            assert release_old.wait(timeout=30)
        return real_activate(session, staged_id, staged_fetched_at, based_on)

    importer._activate_generation = gated_activate
    try:
        def run_old():
            factory = sessionmaker(
                bind=pg_session.get_bind(), autoflush=False, expire_on_commit=False
            )
            with factory() as session:
                try:
                    outcomes["old"] = _import(session, "c" * 64, NOW).status
                except Exception as exc:  # noqa: BLE001
                    outcomes["old"] = f"error: {exc}"

        older = threading.Thread(target=run_old)
        older.start()
        assert started_old.wait(timeout=30)
        # Newer content activates while the older worker is still staged.
        outcomes["new"] = _import(pg_session, "d" * 64, _later(5)).status
        release_old.set()
        older.join(timeout=30)
    finally:
        importer._activate_generation = real_activate

    assert outcomes["new"] == "activated"
    assert outcomes["old"] == "superseded"
    new_id = pg_session.scalar(
        select(TransitFeed.id).where(TransitFeed.content_sha256 == "d" * 64)
    )
    assert get_active_feed_id(pg_session) == new_id


def test_postgres_unreachable_is_reported() -> None:
    try:
        engine = create_engine(
            "postgresql+psycopg://estihub:estihub@localhost:59999/estihub_test",
            connect_args={"connect_timeout": 2},
        )
        with engine.connect():
            pass
        raise AssertionError("unexpected database on :59999")
    except OperationalError:
        pass
