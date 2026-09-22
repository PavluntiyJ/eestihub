"""Routes-for-stop scheduling and feed freshness over staged generations."""

import io
import tempfile
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models import transit as _transit_models  # noqa: F401 (table registration)
from app.models.transit import TransitFeed
from app.services.transit_data import (
    feed_freshness,
    get_active_feed,
    routes_for_stop,
)
from app.services.transit_import import import_feed, parse_feed

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def _base_files(**overrides: str) -> dict[str, str]:
    files = {
        "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nTLL,Tallinn,https://example.com,Europe/Tallinn\n",
        "stops.txt": (
            "stop_id,stop_code,stop_name,stop_lat,stop_lon\n"
            "00123,1001-1,Alpha,59.4370,24.7450\n"
            "S2,,Beta,59.4400,24.7500\n"
            "S3,,Gamma,59.4500,24.7600\n"
        ),
        "routes.txt": (
            "route_id,route_short_name,route_long_name,route_type\n"
            "R1,10,Alpha - Beta,3\n"
            "R2,T1,Alpha Loop,900\n"
        ),
        "trips.txt": (
            "route_id,service_id,trip_id\n"
            "R1,WD,T1\n"
            "R2,WE,T2\n"
            "R1,HOLIDAYS,T3\n"
            "R2,FUT,T8\n"
            "R1,OLD,T9\n"
        ),
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "T1,08:00:00,08:00:00,00123,1\n"
            "T1,08:10:00,08:10:00,S2,2\n"
            "T2,09:00:00,09:00:00,00123,1\n"
            "T3,10:00:00,10:00:00,00123,1\n"
            "T8,11:00:00,11:00:00,00123,1\n"
            "T9,07:00:00,07:00:00,00123,1\n"
        ),
        "calendar.txt": (
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "WD,1,1,1,1,1,0,0,20260101,20261231\n"
            "WE,0,0,0,0,0,1,1,20260101,20261231\n"
            "OLD,1,1,1,1,1,0,0,20200101,20200131\n"
            "FUT,1,1,1,1,1,0,0,20270101,20271231\n"
        ),
        "calendar_dates.txt": (
            "service_id,date,exception_type\n"
            "WD,20260101,2\n"
            "HOLIDAYS,20260101,1\n"
            "WD,20260107,2\n"
        ),
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


def _import_valid(session, sha="a" * 64):
    feed = parse_feed(_make_zip(_base_files()))
    return import_feed(
        session,
        feed,
        source_url="https://transport.tallinn.ee/data/gtfs.zip",
        content_sha256=sha,
        fetched_at=NOW,
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )


@pytest.fixture()
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as current:
        yield current


def active_id(session) -> int:
    from app.services.transit_data import get_active_feed_id

    feed_id = get_active_feed_id(session)
    assert feed_id is not None
    return feed_id


def route_ids(session, feed_id, stop_id, service_date) -> list[str]:
    return [
        route.route_id
        for route in routes_for_stop(session, feed_id, stop_id, service_date)
    ]


def test_weekday_weekend_and_exception_only_services(session) -> None:
    result = _import_valid(session)
    feed_id = result.feed_id
    assert feed_id is not None

    # Tuesday 2026-01-06: WD runs R1, WE and HOLIDAYS do not.
    assert route_ids(session, feed_id, "00123", date(2026, 1, 6)) == ["R1"]
    # Saturday 2026-01-10: WE runs R2.
    assert route_ids(session, feed_id, "00123", date(2026, 1, 10)) == ["R2"]
    # Thursday 2026-01-01: WD removed, HOLIDAYS (exception-only) added.
    assert route_ids(session, feed_id, "00123", date(2026, 1, 1)) == ["R1"]
    # Wednesday 2026-01-07: WD removed, nothing else runs.
    assert route_ids(session, feed_id, "00123", date(2026, 1, 7)) == []
    # Route-less Gamma never has routes, even on a running day.
    assert route_ids(session, feed_id, "S3", date(2026, 1, 6)) == []
    # Unknown stop or unknown feed behave like no service, not an error.
    assert route_ids(session, feed_id, "GHOST", date(2026, 1, 6)) == []
    assert routes_for_stop(session, 999999, "00123", date(2026, 1, 6)) == []


def test_old_generation_remains_queryable(session) -> None:
    first = _import_valid(session)
    assert first.feed_id is not None
    files = _base_files()
    files["routes.txt"] = files["routes.txt"].replace("Alpha Loop", "Alpha Ring", 1)
    second_feed = parse_feed(_make_zip(files))
    from app.services.transit_import import import_feed as _import_feed

    _import_feed(
        session,
        second_feed,
        source_url="https://transport.tallinn.ee/data/gtfs.zip",
        content_sha256="b" * 64,
        fetched_at=NOW,
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )

    assert route_ids(session, first.feed_id, "00123", date(2026, 1, 6)) == ["R1"]
    assert get_active_feed(session) is not None


def test_no_active_feed_returns_none(session) -> None:
    assert get_active_feed(session) is None


def make_feed_row(**overrides):
    row = {
        "checked_at": NOW,
        "source_last_modified": NOW - timedelta(days=1),
        "calendar_start": date(2026, 1, 1),
        "calendar_end": date(2027, 9, 1),
    }
    row.update(overrides)
    return TransitFeed(
        content_sha256="x" * 64,
        source_url="https://transport.tallinn.ee/data/gtfs.zip",
        fetched_at=NOW,
        agency_timezone="Europe/Tallinn",
        stop_count=1,
        route_count=1,
        trip_count=1,
        stop_time_count=1,
        attribution="Tallinn",
        data_license="CC-BY-SA-3.0",
        license_url="https://creativecommons.org/licenses/by-sa/3.0/legalcode.en",
        transformation="test",
        **row,
    )


def freshness(**overrides) -> str:
    now = overrides.pop("now", NOW)
    today = overrides.pop("today", date(2026, 9, 22))
    return feed_freshness(make_feed_row(**overrides), now_utc=now, today=today)


def test_freshness_current() -> None:
    assert freshness() == "current"


def test_freshness_stale_check_age() -> None:
    assert (
        freshness(now=NOW + timedelta(days=7, seconds=1), today=date(2026, 9, 22))
        == "stale"
    )
    assert (
        freshness(now=NOW + timedelta(days=7), today=date(2026, 9, 22)) == "current"
    )


def test_freshness_stale_source_age() -> None:
    assert (
        freshness(source_last_modified=NOW - timedelta(days=30, seconds=1)) == "stale"
    )
    assert freshness(source_last_modified=NOW - timedelta(days=30)) == "current"


def test_freshness_stale_envelope_edges() -> None:
    assert freshness(today=date(2027, 9, 1)) == "current"
    assert freshness(today=date(2027, 9, 2)) == "stale"
    assert freshness(today=date(2025, 12, 31)) == "stale"
    assert freshness(today=date(2026, 1, 1)) == "current"


def test_freshness_stale_envelope_beats_unknown_timestamps() -> None:
    old_envelope = {"calendar_start": date(2025, 1, 1), "calendar_end": date(2025, 12, 31)}
    assert (
        freshness(
            source_last_modified=None, today=date(2026, 9, 22), **old_envelope
        )
        == "stale"
    )
    assert (
        freshness(
            source_last_modified=NOW + timedelta(days=2),
            today=date(2026, 9, 22),
            **old_envelope,
        )
        == "stale"
    )


def test_freshness_unknown_timestamps() -> None:
    assert freshness(source_last_modified=None) == "unknown"
    assert (
        freshness(source_last_modified=NOW + timedelta(hours=25)) == "unknown"
    )
    assert (
        freshness(source_last_modified=NOW + timedelta(hours=24)) == "current"
    )


def test_freshness_naive_datetimes_tolerated() -> None:
    feed = make_feed_row()
    feed.checked_at = feed.checked_at.replace(tzinfo=None)
    assert feed_freshness(feed, now_utc=NOW, today=date(2026, 9, 22)) == "current"
