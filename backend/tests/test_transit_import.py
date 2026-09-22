"""Import validation, staging and activation over tiny synthetic feeds."""

import io
import zipfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models import transit as _transit_models  # noqa: F401 (table registration)
from app.models.transit import TransitFeed, TransitState, TransitStop
from app.services.transit_import import (
    DownloadError,
    FeedError,
    download_source,
    import_feed,
    parse_feed,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def make_zip(files: dict[str, str]) -> str:
    import tempfile

    handle = tempfile.NamedTemporaryFile(prefix="feed-", suffix=".zip", delete=False)
    with zipfile.ZipFile(handle.name, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    handle.close()
    return handle.name


def base_files(**overrides: str) -> dict[str, str]:
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


@pytest.fixture()
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as current:
        yield current


def import_valid(session, files=None, **kwargs):
    feed = parse_feed(make_zip(files or base_files()))
    params = {
        "source_url": "https://transport.tallinn.ee/data/gtfs.zip",
        "content_sha256": kwargs.pop("sha", "a" * 64),
        "fetched_at": kwargs.pop("fetched_at", NOW),
        "checked_at": kwargs.pop("checked_at", NOW),
        "source_last_modified": None,
        "source_etag": None,
    }
    params.update(kwargs)
    return import_feed(session, feed, **params), feed


def test_valid_fixture_stages_exact_counts_and_joins(session) -> None:
    result, _feed = import_valid(session)

    assert result.status == "activated"
    assert result.counts == {
        "stops": 3,
        "routes": 2,
        "trips": 5,
        "stop_times": 6,
        "stop_services": 6,
        "calendars": 4,
        "exceptions": 3,
    }
    assert result.warnings == []
    # Opaque IDs keep leading zeros; route-less Gamma has no pairs.
    pairs = session.execute(
        select(
            _transit_models.TransitStopService.stop_id,
            _transit_models.TransitStopService.route_id,
            _transit_models.TransitStopService.service_id,
        )
    ).all()
    assert ("00123", "R1", "WD") in pairs
    assert ("S2", "R1", "WD") in pairs
    assert ("00123", "R2", "WE") in pairs
    assert ("00123", "R1", "HOLIDAYS") in pairs
    assert not [row for row in pairs if row[0] == "S3"]


def test_modes_derive_from_raw_types(session) -> None:
    import_valid(session)
    modes = {
        row.route_id: (row.route_type, row.mode)
        for row in session.scalars(select(_transit_models.TransitRoute)).all()
    }

    assert modes == {"R1": (3, "bus"), "R2": (900, "tram")}


def test_same_name_stops_are_not_grouped(session) -> None:
    files = base_files()
    files["stops.txt"] = (
        "stop_id,stop_code,stop_name,stop_lat,stop_lon\n"
        "A1,,Same,59.4370,24.7450\n"
        "A2,,Same,59.4371,24.7451\n"
    )
    files["trips.txt"] = "route_id,service_id,trip_id\nR1,WD,T1\nR1,WD,T2\n"
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,A1,1\n"
        "T2,08:00:00,08:00:00,A2,1\n"
    )
    feed = parse_feed(make_zip(files))
    result = import_feed(
        session,
        feed,
        source_url="x",
        content_sha256="b" * 64,
        fetched_at=NOW,
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )

    assert result.status == "activated"
    names = sorted(
        session.scalars(select(TransitStop.stop_name)).all()
    )
    assert names == ["Same", "Same"]
    assert result.counts["stop_services"] == 2


def test_idempotent_sha_records_check_only(session) -> None:
    first, _feed = import_valid(session)
    later = datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc)
    second, _feed = import_valid(session, checked_at=later)

    assert (first.status, second.status) == ("activated", "already_current")
    assert second.feed_id == first.feed_id
    assert session.scalar(select(TransitFeed)).checked_at.replace(
        tzinfo=timezone.utc
    ) == later
    assert session.query(TransitFeed).count() == 1
    assert session.scalar(
        select(TransitState.active_feed_id).where(TransitState.id == 1)
    ) == first.feed_id


def test_changed_feed_activates_and_retains_old(session) -> None:
    first, _feed = import_valid(session)
    files = base_files()
    files["stops.txt"] = files["stops.txt"].replace("Gamma", "Delta")
    feed = parse_feed(make_zip(files))
    second = import_feed(
        session,
        feed,
        source_url="x",
        content_sha256="c" * 64,
        fetched_at=NOW,
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )

    assert second.status == "activated"
    assert session.query(TransitFeed).count() == 2
    assert session.scalar(
        select(TransitState.active_feed_id).where(TransitState.id == 1)
    ) == second.feed_id
    assert session.scalar(
        select(TransitStop.stop_name).where(
            TransitStop.feed_id == first.feed_id, TransitStop.stop_id == "S3"
        )
    ) == "Gamma"


def test_injected_failure_rolls_back_everything(session) -> None:
    import app.services.transit_import as importer

    real_activate = importer._activate_generation

    def boom(*args, **kwargs):
        raise RuntimeError("injected")

    importer._activate_generation = boom
    try:
        feed = parse_feed(make_zip(base_files()))
        with pytest.raises(RuntimeError):
            import_feed(
                session,
                feed,
                source_url="x",
                content_sha256="d" * 64,
                fetched_at=NOW,
                checked_at=NOW,
                source_last_modified=None,
                source_etag=None,
            )
    finally:
        importer._activate_generation = real_activate
    session.rollback()

    assert session.query(TransitFeed).count() == 0
    assert session.scalar(select(TransitState.active_feed_id).where(TransitState.id == 1)) is None


def test_stale_staged_generation_does_not_flip(session) -> None:
    import app.services.transit_import as importer

    new_feed = parse_feed(make_zip(base_files()))
    new_result = import_feed(
        session,
        new_feed,
        source_url="x",
        content_sha256="e" * 64,
        fetched_at=datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc),
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )
    assert new_result.status == "activated"
    old_feed = parse_feed(make_zip(base_files()))
    staged_id_holder: dict = {}

    real_activate = importer._activate_generation

    def capture(session_, staged_id, staged_fetched_at, based_on):
        staged_id_holder["id"] = staged_id
        # Simulate a worker that staged when nothing was active.
        return real_activate(session_, staged_id, staged_fetched_at, None)

    importer._activate_generation = capture
    try:
        stale = import_feed(
            session,
            old_feed,
            source_url="x",
            content_sha256="f" * 64,
            fetched_at=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
            checked_at=NOW,
            source_last_modified=None,
            source_etag=None,
        )
    finally:
        importer._activate_generation = real_activate

    assert stale.status == "superseded"
    assert session.scalar(
        select(TransitState.active_feed_id).where(TransitState.id == 1)
    ) == new_result.feed_id


def test_count_reduction_warns(session, capsys) -> None:
    import_valid(session)
    files = base_files()
    files["stops.txt"] = (
        "stop_id,stop_code,stop_name,stop_lat,stop_lon\n"
        "00123,1001-1,Alpha,59.4370,24.7450\n"
    )
    files["trips.txt"] = "route_id,service_id,trip_id\nR1,WD,T1\n"
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,00123,1\n"
    )
    result, _feed = import_valid(session, files, sha="g" * 64)

    assert result.status == "activated"
    assert any("stops reduced 3 -> 1" in warning for warning in result.warnings)


def base_files_without(*names: str) -> dict[str, str]:
    files = base_files()
    for name in names:
        files.pop(name, None)
    return files


def replace(filename: str, old: str, new: str) -> dict[str, str]:
    files = base_files()
    assert old in files[filename]
    files[filename] = files[filename].replace(old, new, 1)
    return files


@pytest.mark.parametrize(
    "files, reason",
    [
        ({"agency.txt": "x"}, "missing required files"),
        (base_files_without("routes.txt"), "missing required files"),
        (base_files_without("calendar.txt", "calendar_dates.txt"), "calendar"),
        (replace("stops.txt", "stop_lat", "stop_LAT"), "missing headers"),
        (replace("stops.txt", "00123", "00123\n00123"), "duplicate stop_id"),
        (replace("stops.txt", "59.4370", "not-a-number"), "malformed number"),
        (replace("stops.txt", "59.4370", "91.0"), "out of bounds"),
        (replace("routes.txt", ",3\n", ",99\n"), "unsupported route_type"),
        (replace("routes.txt", ",3\n", ",abc\n"), "malformed route_type"),
        (replace("trips.txt", "R1,WD,T1", "RX,WD,T1"), "unknown route_id"),
        (replace("trips.txt", "R1,WD,T1", "R1,NOPE,T1"), "unresolvable service_id"),
        (replace("stop_times.txt", "T1,08:00:00", "TX,08:00:00"), "unknown trip_id"),
        (replace("stop_times.txt", ",00123,1", ",ZZ,1"), "unknown stop_id"),
        (replace("stop_times.txt", "08:00:00,08:00:00", "8am,08:00:00"), "malformed time"),
        (replace("stop_times.txt", "T1,08:00:00,08:00:00,00123,1", "T1,08:00:00,08:00:00,00123,1\nT1,08:05:00,08:05:00,00123,1"), "duplicate stop_sequence"),
        (replace("calendar.txt", "20260101,20261231", "20261231,20260101"), "start after end"),
        (replace("calendar.txt", ",1,1,1,1,1,", ",2,1,1,1,1,"), "weekday flag"),
        (replace("calendar_dates.txt", ",1\n", ",3\n"), "exception_type"),
        (replace("calendar.txt", "WD,1,1,1,1,1,0,0", "WD,1,1,1,1,1,0,0\nWD,1,1,1,1,1,0,0"), "duplicate service_id"),
    ],
)
def test_malformed_feeds_rejected(session, files, reason) -> None:
    del reason
    with pytest.raises(FeedError):
        parse_feed(make_zip(files if isinstance(files, dict) else files()))


def test_missing_parent_reference_rejected(session) -> None:
    files = base_files()
    files["stops.txt"] = (
        "stop_id,stop_code,stop_name,stop_lat,stop_lon,parent_station\n"
        "00123,1001-1,Alpha,59.4370,24.7450,\n"
        "S2,,Beta,59.4400,24.7500,\n"
        "S3,,Gamma,59.4500,24.7600,\n"
        "S4,,Delta,59.4510,24.7610,GHOST\n"
    )
    with pytest.raises(FeedError):
        parse_feed(make_zip(files))


def test_archive_safety_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.transit_import as importer

    monkeypatch.setattr(importer, "MAX_ENTRIES", 2)
    with pytest.raises(FeedError):
        parse_feed(make_zip(base_files()))
    monkeypatch.setattr(importer, "MAX_ROWS_PER_FILE", 1)
    with pytest.raises(FeedError):
        parse_feed(make_zip(base_files()))
    monkeypatch.setattr(importer, "MAX_CELL_BYTES", 4)
    with pytest.raises(FeedError):
        parse_feed(make_zip(base_files()))


def test_download_limits_and_slow_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.transit_import as importer

    class FakeResponse:
        status = 200
        headers: dict = {}

        def __init__(self, chunks):
            self._chunks = list(chunks)

        def read(self, size=-1):
            if not self._chunks:
                return b""
            return self._chunks.pop(0)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    seen_urls: list = []

    def fake_urlopen(request, timeout=None):
        seen_urls.append(request.full_url)
        return FakeResponse([b"x" * 10])

    monkeypatch.setattr(importer, "urlopen", fake_urlopen)
    monkeypatch.setattr(importer, "MAX_COMPRESSED_BYTES", 5)
    with pytest.raises(DownloadError):
        download_source()
    assert seen_urls and seen_urls[0].startswith("https://transport.tallinn.ee/")

    ticks = [0.0]

    def fake_clock():
        ticks[0] += 61.0
        return ticks[0]

    def slow_drip(request, timeout=None):
        return FakeResponse([b"x"])

    monkeypatch.setattr(importer, "urlopen", slow_drip)
    monkeypatch.setattr(importer, "MAX_COMPRESSED_BYTES", 10**9)
    with pytest.raises(DownloadError):
        download_source(deadline_s=60.0, clock=fake_clock)


def test_download_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.transit_import as importer

    def failing(request, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(importer, "urlopen", failing)
    with pytest.raises(DownloadError):
        download_source()
