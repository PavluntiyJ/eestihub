"""Import validation, staging and activation over tiny synthetic feeds."""

import io
import zipfile
from datetime import date, datetime, timezone

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


def test_older_import_after_newer_activation_is_superseded(session) -> None:
    # Review reproduction: activate A fetched at 12:00, then run the normal
    # import path for B fetched at 11:50. B must not overwrite A, no matter
    # that nothing changed during B's own staging.
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
    stale = import_feed(
        session,
        old_feed,
        source_url="x",
        content_sha256="f" * 64,
        fetched_at=datetime(2026, 9, 22, 11, 50, tzinfo=timezone.utc),
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )

    assert stale.status == "superseded"
    assert stale.feed_id is None
    assert session.scalar(
        select(TransitState.active_feed_id).where(TransitState.id == 1)
    ) == new_result.feed_id
    assert session.query(TransitFeed).count() == 1


def test_newer_import_after_older_activation_flips(session) -> None:
    old_feed = parse_feed(make_zip(base_files()))
    old_result = import_feed(
        session,
        old_feed,
        source_url="x",
        content_sha256="e" * 64,
        fetched_at=datetime(2026, 9, 22, 11, 50, tzinfo=timezone.utc),
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )
    assert old_result.status == "activated"
    new_feed = parse_feed(make_zip(base_files()))
    new_result = import_feed(
        session,
        new_feed,
        source_url="x",
        content_sha256="f" * 64,
        fetched_at=datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc),
        checked_at=NOW,
        source_last_modified=None,
        source_etag=None,
    )

    assert new_result.status == "activated"
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


def test_archive_size_limit_rejects() -> None:
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

        def close(self):
            pass

    seen_urls: list = []

    def fake_urlopen(request, timeout=None):
        seen_urls.append(request.full_url)
        return FakeResponse([b"x" * 10])

    real_urlopen = importer.urlopen
    importer.urlopen = fake_urlopen
    real_limit = importer.MAX_COMPRESSED_BYTES
    importer.MAX_COMPRESSED_BYTES = 5
    try:
        with pytest.raises(DownloadError, match="exceeds"):
            download_source()
    finally:
        importer.urlopen = real_urlopen
        importer.MAX_COMPRESSED_BYTES = real_limit
    assert seen_urls and seen_urls[0].startswith("https://transport.tallinn.ee/")


def test_effective_envelope_uses_actual_service_dates(session) -> None:
    del session
    files = base_files()
    files["calendar.txt"] = (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "M,1,0,0,0,0,0,0,20260101,20260110\n"
    )
    files["trips.txt"] = "route_id,service_id,trip_id\nR1,M,T1\n"
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,00123,1\n"
    )
    files["calendar_dates.txt"] = "service_id,date,exception_type\n"
    feed = parse_feed(make_zip(files))

    # 2026-01-05 is the only Monday in range: endpoints are not effective.
    assert (feed.calendar_start, feed.calendar_end) == (
        date(2026, 1, 5),
        date(2026, 1, 5),
    )


def test_single_day_band_without_service_rejected(session) -> None:
    del session
    files = base_files()
    files["calendar.txt"] = (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "M,1,0,0,0,0,0,0,20260106,20260106\n"
    )
    files["trips.txt"] = "route_id,service_id,trip_id\nR1,M,T1\n"
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,00123,1\n"
    )
    files["calendar_dates.txt"] = "service_id,date,exception_type\n"
    with pytest.raises(FeedError, match="no effective service dates"):
        parse_feed(make_zip(files))


def test_removed_only_date_rejected(session) -> None:
    del session
    files = base_files()
    files["calendar.txt"] = (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "M,1,0,0,0,0,0,0,20260105,20260105\n"
    )
    files["trips.txt"] = "route_id,service_id,trip_id\nR1,M,T1\n"
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,00123,1\n"
    )
    files["calendar_dates.txt"] = "service_id,date,exception_type\nM,20260105,2\n"
    with pytest.raises(FeedError, match="no effective service dates"):
        parse_feed(make_zip(files))


def test_implausible_service_range_rejected(session) -> None:
    del session
    files = base_files()
    files["calendar.txt"] = files["calendar.txt"].replace("20260101,20261231", "20000101,29990101")
    with pytest.raises(FeedError, match="implausible service range"):
        parse_feed(make_zip(files))


def test_archive_entry_row_and_cell_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.transit_import as importer

    monkeypatch.setattr(importer, "MAX_ROWS_PER_FILE", 1)
    with pytest.raises(FeedError, match="too many rows"):
        parse_feed(make_zip(base_files()))


def test_archive_cell_limit_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.transit_import as importer

    monkeypatch.setattr(importer, "MAX_CELL_BYTES", 4)
    with pytest.raises(FeedError, match="cell exceeds"):
        parse_feed(make_zip(base_files()))


def _corrupt_member(path: str, member: str, delta: int) -> str:
    import tempfile

    with open(path, "rb") as handle:
        data = bytearray(handle.read())
    archive = zipfile.ZipFile(path)
    try:
        offset = archive.getinfo(member).header_offset
    finally:
        archive.close()
    data[offset + delta] ^= 0xFF
    handle = tempfile.NamedTemporaryFile(prefix="feed-", suffix=".zip", delete=False)
    handle.write(bytes(data))
    handle.close()
    return handle.name


def test_corrupt_crc_in_ignored_shapes_rejected(session) -> None:
    del session
    import app.services.transit_import as importer

    files = base_files()
    files["shapes.txt"] = "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nS,59.4,24.7,1\n"
    corrupted = _corrupt_member(make_zip(files), "shapes.txt", 60)
    with pytest.raises(FeedError):
        parse_feed(corrupted)


def test_corrupt_crc_in_stops_is_invalid_feed_not_traceback(session) -> None:
    del session
    corrupted = _corrupt_member(make_zip(base_files()), "stops.txt", 120)
    with pytest.raises(FeedError):
        parse_feed(corrupted)


def test_duplicate_stop_times_headers_rejected(session) -> None:
    del session
    files = base_files()
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,00123,00123,1\n"
        "T1,08:10:00,08:10:00,S2,S2,2\n"
        "T2,09:00:00,09:00:00,00123,00123,1\n"
        "T3,10:00:00,10:00:00,00123,00123,1\n"
        "T8,11:00:00,11:00:00,00123,00123,1\n"
        "T9,07:00:00,07:00:00,00123,00123,1\n"
    )
    with pytest.raises(FeedError, match="duplicate headers"):
        parse_feed(make_zip(files))


def test_malformed_csv_strict_rejected(session) -> None:
    del session
    files = base_files()
    files["routes.txt"] = files["routes.txt"].replace(
        "R1,10,Alpha - Beta,3\n", 'R1,"Alpha,3\n', 1
    )
    with pytest.raises(FeedError, match="malformed CSV"):
        parse_feed(make_zip(files))


@pytest.mark.parametrize(
    "filename, old, new",
    [
        ("stops.txt", "00123,", "x" * 65 + ","),
        ("stops.txt", "Alpha,", "A" * 256 + ","),
        ("routes.txt", "R1,", "R" * 129 + ","),
        ("trips.txt", "R1,WD,T1", "R1," + "W" * 129 + ",T1"),
    ],
)
def test_overlong_values_rejected(session, filename: str, old: str, new: str) -> None:
    del session
    files = base_files()
    assert old in files[filename]
    files[filename] = files[filename].replace(old, new, 1)
    with pytest.raises(FeedError, match="too long"):
        parse_feed(make_zip(files))


@pytest.mark.parametrize("location_type", ["9", "abc", "-1"])
def test_invalid_location_type_rejected(
    session, location_type: str
) -> None:
    del session
    files = base_files()
    files["stops.txt"] = (
        "stop_id,stop_code,stop_name,stop_lat,stop_lon,location_type\n"
        "00123,1001-1,Alpha,59.4370,24.7450,\n"
        f"S2,,Beta,59.4400,24.7500,{location_type}\n"
        "S3,,Gamma,59.4500,24.7600,\n"
    )
    with pytest.raises(FeedError, match="location_type"):
        parse_feed(make_zip(files))


def test_negative_stop_sequence_rejected(session) -> None:
    del session
    files = base_files()
    files["stop_times.txt"] = files["stop_times.txt"].replace(",00123,1\n", ",00123,-1\n", 1)
    with pytest.raises(FeedError, match="negative stop_sequence"):
        parse_feed(make_zip(files))


@pytest.mark.parametrize("route_type", ["8", "99", "333", "1701", "-1", "abc", "3.5"])
def test_unsupported_route_types_rejected(session, route_type: str) -> None:
    del session
    files = base_files()
    files["routes.txt"] = files["routes.txt"].replace(",3\n", f",{route_type}\n", 1)
    with pytest.raises(FeedError):
        parse_feed(make_zip(files))


@pytest.mark.parametrize(
    "route_type, mode", [("0", "tram"), ("901", "other"), ("700", "bus"), ("701", "other"), ("11", "trolleybus"), ("1501", "other"), ("100", "other")]
)
def test_supported_route_types_map_modes(session, route_type: str, mode: str) -> None:
    files = base_files()
    files["routes.txt"] = (
        "route_id,route_short_name,route_long_name,route_type\n"
        f"RX,9,Long,{route_type}\n"
    )
    files["trips.txt"] = "route_id,service_id,trip_id\nRX,WD,TX\n"
    files["stop_times.txt"] = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "TX,08:00:00,08:00:00,00123,1\n"
    )
    result, _feed = import_valid(session, files=files, sha=route_type + "z" * 60)
    assert result.status == "activated"
    stored = session.scalar(
        select(_transit_models.TransitRoute.mode).where(
            _transit_models.TransitRoute.route_id == "RX"
        )
    )
    assert stored == mode


def test_slow_drip_stops_at_total_deadline_and_cleans_up() -> None:
    import glob
    import os
    import tempfile
    import threading
    import time

    import app.services.transit_import as importer

    release = threading.Event()

    class DripResponse:
        status = 200
        headers: dict = {}
        closed = False

        def read(self, size=-1):
            # One byte per blocking call, forever: the socket timeout never
            # fires because every call returns quickly with data.
            if release.wait(timeout=30):
                return b""
            return b"x"

        def close(self):
            self.closed = True
            release.set()

    def dripping(request, timeout=None):
        return DripResponse()

    before = set(glob.glob(os.path.join(tempfile.gettempdir(), "gtfs-*.zip")))
    real_urlopen = importer.urlopen
    importer.urlopen = dripping
    started = time.monotonic()
    try:
        with pytest.raises(DownloadError, match="deadline"):
            download_source(deadline_s=1.0, timeout_s=30.0)
    finally:
        importer.urlopen = real_urlopen
    elapsed = time.monotonic() - started
    assert elapsed < 15
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), "gtfs-*.zip")))
    assert after - before == set()


def test_download_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.transit_import as importer

    def failing(request, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(importer, "urlopen", failing)
    with pytest.raises(DownloadError):
        download_source()


def test_cli_validate_only_reports_counts() -> None:
    import subprocess
    import sys

    repo_backend = __file__.rsplit("tests", 1)[0]
    archive = make_zip(base_files())
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.import_gtfs", "--validate-only", "--file", archive],
        cwd=repo_backend,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "validated: stops=3 routes=2" in proc.stdout


def test_cli_missing_file_reports_concise_error(tmp_path) -> None:
    import subprocess
    import sys

    repo_backend = __file__.rsplit("tests", 1)[0]
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.import_gtfs", "--file", str(tmp_path / "nope.zip")],
        cwd=repo_backend,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 1
    assert proc.stdout.startswith("error:")
    assert "Traceback" not in proc.stdout + proc.stderr


def test_cli_invalid_metadata_flag_exits_usage_error(tmp_path) -> None:
    import subprocess
    import sys

    repo_backend = __file__.rsplit("tests", 1)[0]
    archive = make_zip(base_files())
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.import_gtfs",
            "--file",
            archive,
            "--last-modified",
            "not-a-date",
        ],
        cwd=repo_backend,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0
    assert "Traceback" not in proc.stdout + proc.stderr


def test_cli_unavailable_database_reports_concisely(tmp_path) -> None:
    import os
    import subprocess
    import sys

    repo_backend = __file__.rsplit("tests", 1)[0]
    archive = make_zip(base_files())
    env = dict(os.environ)
    # Unresolvable host fails fast; a refused localhost port can hang the
    # OS connect path, which would test timeouts instead of the message.
    env["DATABASE_URL"] = "postgresql+psycopg://estihub:estihub@nonexistent.invalid/estihub_test"
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.import_gtfs", "--file", archive],
        cwd=repo_backend,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 3
    assert "database unavailable" in proc.stdout
    assert "SELECT" not in proc.stdout + proc.stderr
