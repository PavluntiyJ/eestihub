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
EXPLICIT_TEST_DATABASE_URL = "TRANSIT_TEST_DATABASE_URL" in os.environ


def _assert_test_database(url: str) -> None:
    name = url.rsplit("/", 1)[-1].split("?")[0]
    if not name.endswith("_test"):
        pytest.fail(
            f"refusing to clean non-test database {name!r}: "
            "point TRANSIT_TEST_DATABASE_URL at a disposable *_test database"
        )


def _engine_or_skip():
    _assert_test_database(TEST_DATABASE_URL)
    try:
        engine = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 5})
        with engine.connect():
            pass
    except Exception as exc:
        if EXPLICIT_TEST_DATABASE_URL:
            # An explicitly configured test database must work, not skip.
            raise
        pytest.skip(f"local Postgres unavailable: {exc}")
    return engine


def test_only_test_databases_are_cleaned() -> None:
    from _pytest.outcomes import Failed

    with pytest.raises(Failed):
        _assert_test_database(
            "postgresql+psycopg://estihub:estihub@localhost:5432/estihub_dev"
        )
    _assert_test_database(
        "postgresql+psycopg://estihub:estihub@localhost:5432/estihub_test"
    )


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

    def gated_activate(session, staged_id, staged_fetched_at):
        if staged_fetched_at <= NOW:
            started_old.set()
            assert release_old.wait(timeout=30)
        return real_activate(session, staged_id, staged_fetched_at)

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


def test_postgres_concurrent_first_imports_newer_wins(pg_session) -> None:
    entered = threading.Event()
    release = threading.Event()
    outcomes: dict = {}

    import app.services.transit_import as importer

    real_activate = importer._activate_generation

    def gated_activate(session, staged_id, staged_fetched_at):
        entered.set()
        assert release.wait(timeout=30)
        return real_activate(session, staged_id, staged_fetched_at)

    importer._activate_generation = gated_activate

    def run_import(sha, fetched_at, key):
        factory = sessionmaker(
            bind=pg_session.get_bind(), autoflush=False, expire_on_commit=False
        )
        with factory() as session:
            try:
                outcomes[key] = _import(session, sha, fetched_at).status
            except Exception as exc:  # noqa: BLE001
                outcomes[key] = f"error: {exc}"

    try:
        first = threading.Thread(target=run_import, args=("e" * 64, NOW, "older"))
        second = threading.Thread(target=run_import, args=("f" * 64, _later(5), "newer"))
        first.start()
        second.start()
        assert entered.wait(timeout=30)
        # Both workers staged; let the older flip first, then the newer.
        release.set()
        first.join(timeout=60)
        second.join(timeout=60)
    finally:
        importer._activate_generation = real_activate

    # No state row existed: both workers stage concurrently, and the newer
    # content ends up active regardless of flip order (older-first flips,
    # then newer flips over it; newer-first supersedes the older flip).
    assert outcomes["newer"] == "activated"
    assert outcomes["older"] in ("activated", "superseded")
    new_id = pg_session.scalar(
        select(TransitFeed.id).where(TransitFeed.content_sha256 == "f" * 64)
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


def test_postgres_same_sha_first_flush_race_recovers(pg_session, monkeypatch) -> None:
    """Both workers miss the SHA lookup, then contend on the first INSERT."""
    from sqlalchemy import event
    from app.models.transit import TransitFeed

    barrier = threading.Barrier(2)
    outcomes = []
    factory = sessionmaker(bind=pg_session.get_bind(), autoflush=False, expire_on_commit=False)

    def run():
        with factory() as session:
            synchronized = False

            def before_flush(current, *_args):
                nonlocal synchronized
                if not synchronized and any(isinstance(row, TransitFeed) for row in current.new):
                    synchronized = True
                    barrier.wait(timeout=20)

            event.listen(session, "before_flush", before_flush)
            try:
                outcomes.append(_import(session, "9" * 64, NOW).status)
            except Exception as exc:
                outcomes.append(type(exc).__name__)

    workers = [threading.Thread(target=run) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=40)
        assert not worker.is_alive()
    assert sorted(outcomes) == ["activated", "already_current"]
    assert pg_session.query(TransitFeed).count() == 1
