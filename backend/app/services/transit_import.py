"""Versioned Tallinn GTFS import from the fixed In-AKS distribution.

Pipeline: download (bounded) -> validate fully -> idempotent SHA check ->
stage one generation -> atomic pointer flip, all inside a single database
transaction for the staging part. Download and parsing never run inside the
activation transaction. There is no retry, no fallback source and no reverse
endpoint. Failures leave the previously active generation untouched.
"""

from __future__ import annotations

import csv
import hashlib
import io
import tempfile
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.transit import (
    TransitCalendar,
    TransitCalendarException,
    TransitFeed,
    TransitRoute,
    TransitState,
    TransitStop,
    TransitStopService,
)

SOURCE_URL = "https://transport.tallinn.ee/data/gtfs.zip"
USER_AGENT = "EestiHub-transit-import/1.0"
SOCKET_TIMEOUT_SECONDS = 10.0
TOTAL_DOWNLOAD_DEADLINE_SECONDS = 60.0
MAX_COMPRESSED_BYTES = 50 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_ENTRY_BYTES = 100 * 1024 * 1024
MAX_ENTRIES = 32
MAX_ROWS_PER_FILE = 2_000_000
MAX_CELL_BYTES = 64 * 1024
CHUNK_BYTES = 65536

REQUIRED_FILES = frozenset(
    {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}
)
CALENDAR_FILES = frozenset({"calendar.txt", "calendar_dates.txt"})

DATA_LICENSE = "CC-BY-SA-3.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/3.0/legalcode.en"
ATTRIBUTION = (
    "Tallinn public transport stops and routes (Tallinna ühistranspordi "
    "peatused ja marsruudid), Maa- ja Ruumiamet via transport.tallinn.ee, "
    "registry https://avaandmed.eesti.ee/api/datasets/5ccad39d-98a0-4ac4-ba0a-233ad5a83604. "
    "Derived transit data under CC BY-SA 3.0."
)
TRANSFORMATION = (
    "Normalized subset of the GTFS distribution for nearby-stop lookup: "
    "stops, routes, deduplicated (stop, route, service) pairs, weekday "
    "calendars and date exceptions. Trips, stop times, shapes and agency "
    "rows are transient join inputs and are not stored."
)

# GTFS static route_type values 0-7, 11, 12 plus the extended 100-1700 code
# space (https://developers.google.com/transit/gtfs/reference/extended-route-types).
_VALID_ROUTE_TYPES = (
    frozenset({0, 1, 2, 3, 4, 5, 6, 7, 11, 12}) | frozenset(range(100, 1701))
)
_TRAM_TYPES = frozenset({0, 900})
_BUS_TYPES = frozenset({3, 700})
_TROLLEYBUS_TYPES = frozenset({11, 800})


class FeedError(Exception):
    """The archive or its data failed validation."""


class DownloadError(Exception):
    """The fixed source could not be fetched within bounds."""


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        # SQLite returns naive datetimes for timezone-aware columns.
        return value.replace(tzinfo=timezone.utc)
    return value


@dataclass
class StopRow:
    stop_id: str
    stop_code: str | None
    stop_name: str
    stop_lat: float
    stop_lon: float
    parent_station: str | None
    location_type: str | None


@dataclass
class RouteRow:
    route_id: str
    short_name: str | None
    long_name: str | None
    route_type: int
    mode: str


@dataclass
class ParsedFeed:
    agency_timezone: str
    stops: dict[str, StopRow] = field(default_factory=dict)
    routes: dict[str, RouteRow] = field(default_factory=dict)
    # trip_id -> (route_id, service_id)
    trips: dict[str, tuple[str, str]] = field(default_factory=dict)
    stop_services: set[tuple[str, str, str]] = field(default_factory=set)
    calendars: dict[str, dict] = field(default_factory=dict)
    exceptions: list[tuple[str, date, int]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    calendar_start: date | None = None
    calendar_end: date | None = None


@dataclass
class DownloadedFeed:
    path: str
    content_sha256: str
    fetched_at: datetime
    source_last_modified: datetime | None
    source_etag: str | None


@dataclass
class ImportResult:
    status: str  # "activated" | "already_current" | "superseded"
    feed_id: int | None
    content_sha256: str
    counts: dict[str, int]
    warnings: list[str]


def _fail(reason: str) -> FeedError:
    return FeedError(reason)


def download_source(
    *,
    timeout_s: float = SOCKET_TIMEOUT_SECONDS,
    deadline_s: float = TOTAL_DOWNLOAD_DEADLINE_SECONDS,
    max_bytes: int | None = None,
    user_agent: str = USER_AGENT,
    clock=time.monotonic,
) -> DownloadedFeed:
    """Fetch the fixed source into bounded temporary storage.

    The socket timeout covers each blocking operation while the monotonic
    deadline bounds the total wall time, so slow-drip responses stop as
    well as silent ones. No retry loop. The size cap resolves at call time
    so tests can tighten it with monkeypatch.
    """
    if max_bytes is None:
        max_bytes = MAX_COMPRESSED_BYTES
    request = Request(SOURCE_URL, headers={"User-Agent": user_agent})
    started = clock()
    total = 0
    handle = tempfile.NamedTemporaryFile(
        prefix="gtfs-", suffix=".zip", delete=False
    )
    try:
        try:
            response = urlopen(request, timeout=timeout_s)
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise DownloadError(f"fetch failed: {exc}") from exc
        with response:
            if response.status != 200:
                raise DownloadError(f"unexpected HTTP status {response.status}")
            while True:
                if clock() - started > deadline_s:
                    raise DownloadError("download deadline exceeded")
                try:
                    chunk = response.read(CHUNK_BYTES)
                except (TimeoutError, OSError) as exc:
                    raise DownloadError(f"stalled download: {exc}") from exc
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise DownloadError("archive exceeds size limit")
                handle.write(chunk)
    except BaseException:
        handle.close()
        raise
    handle.close()
    last_modified = _parse_http_date(response.headers.get("Last-Modified"))
    etag = response.headers.get("ETag")
    digest = _sha256_file(handle.name)
    return DownloadedFeed(
        path=handle.name,
        content_sha256=digest,
        fetched_at=datetime.now(timezone.utc),
        source_last_modified=last_modified,
        source_etag=etag[:255] if etag else None,
    )


def _parse_http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def prepare_local_file(
    path: str, *, last_modified: str | None = None, etag: str | None = None
) -> DownloadedFeed:
    """Validate a manually supplied archive without downloading.

    Source timestamps stay unknown unless supplied as validated metadata.
    The caller's file is never deleted.
    """
    import os

    if not os.path.isfile(path):
        raise FeedError(f"file not found: {path}")
    if os.path.getsize(path) > MAX_COMPRESSED_BYTES:
        raise FeedError("local archive exceeds size limit")
    parsed_last_modified = None
    if last_modified is not None:
        parsed_last_modified = _parse_http_date(last_modified)
        if parsed_last_modified is None:
            raise FeedError("--last-modified is not a valid HTTP date")
    if etag is not None and len(etag) > 255:
        raise FeedError("--etag is too long")
    return DownloadedFeed(
        path=path,
        content_sha256=_sha256_file(path),
        fetched_at=datetime.now(timezone.utc),
        source_last_modified=parsed_last_modified,
        source_etag=etag,
    )


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_zip(path: str) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise _fail(f"not a zip archive: {exc}") from exc
    return archive


def _check_archive_members(archive: zipfile.ZipFile) -> None:
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise _fail("duplicate member names")
    if len(names) > MAX_ENTRIES:
        raise _fail(f"too many entries: {len(names)}")
    total_uncompressed = 0
    for info in archive.infolist():
        name = info.filename
        if (
            name.startswith("/")
            or ".." in name.split("/")
            or "\\" in name
            or name.startswith("~")
        ):
            raise _fail(f"unsafe member path: {name!r}")
        if info.is_dir():
            continue
        if info.flag_bits & 0x1:
            raise _fail(f"encrypted member: {name!r}")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise _fail(f"symlink member: {name!r}")
        lowered = name.lower()
        if lowered.endswith((".zip", ".jar", ".kmz", ".cbz")):
            raise _fail(f"nested archive member: {name!r}")
        if info.file_size > MAX_ENTRY_BYTES:
            raise _fail(f"entry too large: {name!r}")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise _fail("uncompressed size exceeds limit")
    present = {name for name in names if "/" not in name.rstrip("/")}
    missing = REQUIRED_FILES - present
    if missing:
        raise _fail(f"missing required files: {', '.join(sorted(missing))}")
    if not (CALENDAR_FILES & present):
        raise _fail("at least one calendar file is required")


def _read_rows(
    archive: zipfile.ZipFile, name: str, required: frozenset[str]
) -> tuple[list[str], list[list[str]]]:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise _fail(f"missing file: {name}") from exc
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _fail(f"{name}: invalid UTF-8") from exc
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration:
        raise _fail(f"{name}: empty file") from None
    missing = required - set(headers)
    if missing:
        raise _fail(f"{name}: missing headers: {', '.join(sorted(missing))}")
    if len(headers) != len(set(headers)):
        raise _fail(f"{name}: duplicate headers")
    rows: list[list[str]] = []
    for lineno, fields in enumerate(reader, start=2):
        if len(fields) != len(headers):
            raise _fail(f"{name} line {lineno}: ragged row")
        for cell in fields:
            if len(cell.encode("utf-8")) > MAX_CELL_BYTES:
                raise _fail(f"{name} line {lineno}: cell exceeds size limit")
        rows.append(fields)
        if len(rows) > MAX_ROWS_PER_FILE:
            raise _fail(f"{name}: too many rows")
    return headers, rows


def _parse_date(value: str, what: str) -> date:
    if len(value) != 8 or not value.isdigit():
        raise _fail(f"{what}: malformed date {value!r}")
    try:
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as exc:
        raise _fail(f"{what}: invalid date {value!r}") from exc


def _parse_bool_flag(value: str, what: str) -> bool:
    if value not in ("0", "1"):
        raise _fail(f"{what}: weekday flag must be 0 or 1, got {value!r}")
    return value == "1"


def _parse_float(value: str, what: str) -> float:
    try:
        number = float(value.strip())
    except ValueError as exc:
        raise _fail(f"{what}: malformed number {value!r}") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise _fail(f"{what}: non-finite number {value!r}")
    return number


def _parse_route_type(value: str) -> int:
    try:
        route_type = int(value.strip())
    except ValueError as exc:
        raise _fail(f"malformed route_type {value!r}") from exc
    if route_type not in _VALID_ROUTE_TYPES:
        raise _fail(f"unsupported route_type {value!r}")
    return route_type


def _derive_mode(route_type: int) -> str:
    if route_type in _TRAM_TYPES:
        return "tram"
    if route_type in _BUS_TYPES:
        return "bus"
    if route_type in _TROLLEYBUS_TYPES:
        return "trolleybus"
    return "other"


def parse_feed(path: str) -> ParsedFeed:
    """Validate an archive fully and return the normalized in-memory feed."""
    archive = _open_zip(path)
    with archive:
        _check_archive_members(archive)
        feed = ParsedFeed(agency_timezone="")
        _parse_agency(archive, feed)
        _parse_stops(archive, feed)
        _parse_routes(archive, feed)
        _parse_trips(archive, feed)
        _parse_stop_times(archive, feed)
        _parse_calendars(archive, feed)
        _resolve_services(feed)
    return feed


def _parse_agency(archive: zipfile.ZipFile, feed: ParsedFeed) -> None:
    headers, rows = _read_rows(archive, "agency.txt", frozenset({"agency_timezone"}))
    if not rows:
        raise _fail("agency.txt: no rows")
    zones = {dict(zip(headers, row))["agency_timezone"] for row in rows}
    if len(zones) != 1:
        raise _fail("agency.txt: ambiguous timezones")
    timezone_name = next(iter(zones))
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise _fail(f"agency.txt: unknown timezone {timezone_name!r}") from exc
    feed.agency_timezone = timezone_name


def _parse_stops(archive: zipfile.ZipFile, feed: ParsedFeed) -> None:
    headers, rows = _read_rows(
        archive,
        "stops.txt",
        frozenset({"stop_id", "stop_name", "stop_lat", "stop_lon"}),
    )
    if not rows:
        raise _fail("stops.txt: no rows")
    index = {name: position for position, name in enumerate(headers)}
    for lineno, fields in enumerate(rows, start=2):
        record = dict(zip(headers, fields))
        stop_id = record["stop_id"]
        if not stop_id:
            raise _fail(f"stops.txt line {lineno}: empty stop_id")
        if stop_id in feed.stops:
            raise _fail(f"stops.txt line {lineno}: duplicate stop_id")
        latitude = _parse_float(record["stop_lat"], f"stops.txt line {lineno}")
        longitude = _parse_float(record["stop_lon"], f"stops.txt line {lineno}")
        if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
            raise _fail(f"stops.txt line {lineno}: coordinates out of bounds")
        if not record["stop_name"]:
            raise _fail(f"stops.txt line {lineno}: empty stop_name")
        parent = record.get("parent_station") or None
        feed.stops[stop_id] = StopRow(
            stop_id=stop_id,
            stop_code=record.get("stop_code") or None,
            stop_name=record["stop_name"],
            stop_lat=latitude,
            stop_lon=longitude,
            parent_station=parent,
            location_type=record.get("location_type") or None,
        )
    for stop in feed.stops.values():
        if stop.parent_station is not None and stop.parent_station not in feed.stops:
            raise _fail(f"stops.txt: unknown parent_station {stop.parent_station!r}")
    _ = index


def _parse_routes(archive: zipfile.ZipFile, feed: ParsedFeed) -> None:
    headers, rows = _read_rows(
        archive, "routes.txt", frozenset({"route_id", "route_type"})
    )
    if not rows:
        raise _fail("routes.txt: no rows")
    for lineno, fields in enumerate(rows, start=2):
        record = dict(zip(headers, fields))
        route_id = record["route_id"]
        if not route_id:
            raise _fail(f"routes.txt line {lineno}: empty route_id")
        if route_id in feed.routes:
            raise _fail(f"routes.txt line {lineno}: duplicate route_id")
        route_type = _parse_route_type(record["route_type"])
        feed.routes[route_id] = RouteRow(
            route_id=route_id,
            short_name=record.get("route_short_name") or None,
            long_name=record.get("route_long_name") or None,
            route_type=route_type,
            mode=_derive_mode(route_type),
        )


def _parse_trips(archive: zipfile.ZipFile, feed: ParsedFeed) -> None:
    headers, rows = _read_rows(
        archive, "trips.txt", frozenset({"route_id", "service_id", "trip_id"})
    )
    if not rows:
        raise _fail("trips.txt: no rows")
    for lineno, fields in enumerate(rows, start=2):
        record = dict(zip(headers, fields))
        trip_id = record["trip_id"]
        if not trip_id:
            raise _fail(f"trips.txt line {lineno}: empty trip_id")
        if trip_id in feed.trips:
            raise _fail(f"trips.txt line {lineno}: duplicate trip_id")
        if record["route_id"] not in feed.routes:
            raise _fail(f"trips.txt line {lineno}: unknown route_id")
        if not record["service_id"]:
            raise _fail(f"trips.txt line {lineno}: empty service_id")
        feed.trips[trip_id] = (record["route_id"], record["service_id"])


def _parse_stop_times(archive: zipfile.ZipFile, feed: ParsedFeed) -> None:
    try:
        raw = archive.read("stop_times.txt")
    except KeyError as exc:
        raise _fail("missing file: stop_times.txt") from exc
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _fail("stop_times.txt: invalid UTF-8") from exc
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration:
        raise _fail("stop_times.txt: empty file") from None
    required = frozenset(
        {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"}
    )
    missing = required - set(headers)
    if missing:
        raise _fail(f"stop_times.txt: missing headers: {', '.join(sorted(missing))}")
    index = {name: position for position, name in enumerate(headers)}
    sequences: dict[str, set[int]] = defaultdict(set)
    count = 0
    for lineno, fields in enumerate(reader, start=2):
        if len(fields) != len(headers):
            raise _fail(f"stop_times.txt line {lineno}: ragged row")
        for cell in fields:
            if len(cell.encode("utf-8")) > MAX_CELL_BYTES:
                raise _fail(f"stop_times.txt line {lineno}: cell exceeds size limit")
        count += 1
        if count > MAX_ROWS_PER_FILE:
            raise _fail("stop_times.txt: too many rows")
        trip_id = fields[index["trip_id"]]
        stop_id = fields[index["stop_id"]]
        if trip_id not in feed.trips:
            raise _fail(f"stop_times.txt line {lineno}: unknown trip_id")
        if stop_id not in feed.stops:
            raise _fail(f"stop_times.txt line {lineno}: unknown stop_id")
        try:
            sequence = int(fields[index["stop_sequence"]].strip())
        except ValueError as exc:
            raise _fail(
                f"stop_times.txt line {lineno}: malformed stop_sequence"
            ) from exc
        if sequence in sequences[trip_id]:
            raise _fail(
                f"stop_times.txt line {lineno}: duplicate stop_sequence"
            )
        sequences[trip_id].add(sequence)
        for column in ("arrival_time", "departure_time"):
            _parse_gtfs_time(fields[index[column]], f"stop_times.txt line {lineno}")
        route_id, _service_id = feed.trips[trip_id]
        feed.stop_services.add((stop_id, route_id, feed.trips[trip_id][1]))
    if count == 0:
        raise _fail("stop_times.txt: no rows")
    feed.counts["stop_times"] = count


def _parse_gtfs_time(value: str, what: str) -> None:
    parts = value.strip().split(":")
    if len(parts) != 3:
        raise _fail(f"{what}: malformed time {value!r}")
    hours, minutes, seconds = parts
    if (
        not hours.isdigit()
        or len(minutes) != 2
        or len(seconds) != 2
        or not minutes.isdigit()
        or not seconds.isdigit()
        or int(minutes) > 59
        or int(seconds) > 59
    ):
        raise _fail(f"{what}: malformed time {value!r}")


_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _parse_calendars(archive: zipfile.ZipFile, feed: ParsedFeed) -> None:
    names = set(archive.namelist())
    if "calendar.txt" in names:
        headers, rows = _read_rows(
            archive,
            "calendar.txt",
            frozenset({"service_id", *_WEEKDAYS, "start_date", "end_date"}),
        )
        for lineno, fields in enumerate(rows, start=2):
            record = dict(zip(headers, fields))
            service_id = record["service_id"]
            if not service_id:
                raise _fail(f"calendar.txt line {lineno}: empty service_id")
            if service_id in feed.calendars:
                raise _fail(f"calendar.txt line {lineno}: duplicate service_id")
            flags = {
                day: _parse_bool_flag(record[day], f"calendar.txt line {lineno}")
                for day in _WEEKDAYS
            }
            start = _parse_date(record["start_date"], f"calendar.txt line {lineno}")
            end = _parse_date(record["end_date"], f"calendar.txt line {lineno}")
            if start > end:
                raise _fail(f"calendar.txt line {lineno}: start after end")
            feed.calendars[service_id] = {
                "flags": flags,
                "start_date": start,
                "end_date": end,
            }
    if "calendar_dates.txt" in names:
        headers, rows = _read_rows(
            archive,
            "calendar_dates.txt",
            frozenset({"service_id", "date", "exception_type"}),
        )
        seen: set[tuple[str, date]] = set()
        for lineno, fields in enumerate(rows, start=2):
            record = dict(zip(headers, fields))
            if not record["service_id"]:
                raise _fail(f"calendar_dates.txt line {lineno}: empty service_id")
            day = _parse_date(record["date"], f"calendar_dates.txt line {lineno}")
            if record["exception_type"] not in ("1", "2"):
                raise _fail(
                    f"calendar_dates.txt line {lineno}: exception_type must be 1 or 2"
                )
            key = (record["service_id"], day)
            if key in seen:
                raise _fail(f"calendar_dates.txt line {lineno}: duplicate exception")
            seen.add(key)
            feed.exceptions.append((record["service_id"], day, int(record["exception_type"])))


def _resolve_services(feed: ParsedFeed) -> None:
    known_services = set(feed.calendars) | {
        service_id for service_id, _day, _kind in feed.exceptions
    }
    for trip_id, (_route_id, service_id) in feed.trips.items():
        if service_id not in known_services:
            raise _fail(f"trips.txt: unresolvable service_id for trip {trip_id!r}")
    effective: list[date] = []
    for service_id in {service for _r, service in feed.trips.values()}:
        calendar = feed.calendars.get(service_id)
        if calendar is not None and any(calendar["flags"].values()):
            effective.append(calendar["start_date"])
            effective.append(calendar["end_date"])
        for exception_service, day, kind in feed.exceptions:
            if exception_service == service_id and kind == 1:
                effective.append(day)
    if not effective:
        raise _fail("no effective service dates")
    feed.calendar_start = min(effective)
    feed.calendar_end = max(effective)
    feed.counts.update(
        {
            "stops": len(feed.stops),
            "routes": len(feed.routes),
            "trips": len(feed.trips),
            "stop_services": len(feed.stop_services),
            "calendars": len(feed.calendars),
            "exceptions": len(feed.exceptions),
        }
    )


def _warn_on_reduction(
    session: Session, active_id: int | None, feed: ParsedFeed
) -> list[str]:
    warnings: list[str] = []
    if active_id is None:
        return warnings
    active = session.get(TransitFeed, active_id)
    if active is None:
        return warnings
    for label, old, new in (
        ("stops", active.stop_count, len(feed.stops)),
        ("routes", active.route_count, len(feed.routes)),
        ("trips", active.trip_count, len(feed.trips)),
    ):
        if new < old:
            warnings.append(f"warning: {label} reduced {old} -> {new} for review")
    return warnings


def _activate_generation(
    session: Session,
    staged_id: int,
    staged_fetched_at: datetime,
    based_on: int | None,
) -> str:
    """Flip the singleton pointer under a row lock with compare-and-swap.

    Returns "activated", or "superseded" when another activation landed
    after this import staged and the staged content is older. A first
    import has no row to protect; a concurrent first-import primary-key
    race surfaces as IntegrityError for the caller to map.
    """
    state = session.scalar(
        select(TransitState).where(TransitState.id == 1).with_for_update()
    )
    if state is None:
        state = TransitState(id=1, active_feed_id=None)
        session.add(state)
        session.flush()
    current_active_id = state.active_feed_id
    current_active = (
        session.get(TransitFeed, current_active_id)
        if current_active_id is not None
        else None
    )
    if current_active is not None and current_active_id != based_on:
        current_fetched = as_aware_utc(current_active.fetched_at)
        if not as_aware_utc(staged_fetched_at) >= current_fetched:
            return "superseded"
    state.active_feed_id = staged_id
    return "activated"


def import_feed(
    session: Session,
    feed: ParsedFeed,
    *,
    source_url: str,
    content_sha256: str,
    fetched_at: datetime,
    checked_at: datetime,
    source_last_modified: datetime | None,
    source_etag: str | None,
) -> ImportResult:
    """Stage one generation and flip the active pointer atomically.

    Download and parsing happen before this call, outside the transaction.
    Everything below commits once; any failure rolls the staging back and
    the previous pointer stays intact. An identical SHA only records a new
    successful check time. A staged generation older than the current
    activation is rolled back as superseded instead of flipping.
    """
    existing = session.scalar(
        select(TransitFeed).where(TransitFeed.content_sha256 == content_sha256)
    )
    if existing is not None:
        existing.checked_at = checked_at
        session.commit()
        return ImportResult(
            status="already_current",
            feed_id=existing.id,
            content_sha256=content_sha256,
            counts=dict(feed.counts),
            warnings=[],
        )
    based_on = session.scalar(select(TransitState.active_feed_id).where(TransitState.id == 1))
    warnings = _warn_on_reduction(session, based_on, feed)
    staged = TransitFeed(
        content_sha256=content_sha256,
        source_url=source_url,
        fetched_at=fetched_at,
        checked_at=checked_at,
        source_last_modified=source_last_modified,
        source_etag=source_etag,
        agency_timezone=feed.agency_timezone,
        calendar_start=feed.calendar_start,
        calendar_end=feed.calendar_end,
        stop_count=len(feed.stops),
        route_count=len(feed.routes),
        trip_count=len(feed.trips),
        stop_time_count=feed.counts.get("stop_times", 0),
        attribution=ATTRIBUTION,
        data_license=DATA_LICENSE,
        license_url=LICENSE_URL,
        transformation=TRANSFORMATION,
    )
    session.add(staged)
    session.flush()
    for stop in feed.stops.values():
        session.add(
            TransitStop(
                feed_id=staged.id,
                stop_id=stop.stop_id,
                stop_code=stop.stop_code,
                stop_name=stop.stop_name,
                stop_lat=stop.stop_lat,
                stop_lon=stop.stop_lon,
                parent_station=stop.parent_station,
                location_type=stop.location_type,
            )
        )
    for route in feed.routes.values():
        session.add(
            TransitRoute(
                feed_id=staged.id,
                route_id=route.route_id,
                short_name=route.short_name,
                long_name=route.long_name,
                route_type=route.route_type,
                mode=route.mode,
            )
        )
    for stop_id, route_id, service_id in sorted(feed.stop_services):
        session.add(
            TransitStopService(
                feed_id=staged.id,
                stop_id=stop_id,
                route_id=route_id,
                service_id=service_id,
            )
        )
    for service_id, calendar in feed.calendars.items():
        session.add(
            TransitCalendar(
                feed_id=staged.id,
                service_id=service_id,
                **{day: calendar["flags"][day] for day in _WEEKDAYS},
                start_date=calendar["start_date"],
                end_date=calendar["end_date"],
            )
        )
    for service_id, day, kind in feed.exceptions:
        session.add(
            TransitCalendarException(
                feed_id=staged.id,
                service_id=service_id,
                exception_date=day,
                exception_type=kind,
            )
        )
    session.flush()
    outcome = _activate_generation(session, staged.id, fetched_at, based_on)
    if outcome == "superseded":
        session.rollback()
        return ImportResult(
            status="superseded",
            feed_id=None,
            content_sha256=content_sha256,
            counts=dict(feed.counts),
            warnings=warnings,
        )
    session.commit()
    return ImportResult(
        status="activated",
        feed_id=staged.id,
        content_sha256=content_sha256,
        counts=dict(feed.counts),
        warnings=warnings,
    )
