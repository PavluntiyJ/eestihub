"""Versioned Tallinn GTFS import from the fixed transport distribution.

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
import json
import os
import tempfile
import zipfile
import zlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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
    "peatused ja marsruudid) via transport.tallinn.ee, registry "
    "https://avaandmed.eesti.ee/api/datasets/5ccad39d-98a0-4ac4-ba0a-233ad5a83604. "
    "Derived transit data under CC BY-SA 3.0."
)
TRANSFORMATION = (
    "Normalized subset of the GTFS distribution for nearby-stop lookup: "
    "stops, routes, deduplicated (stop, route, service) pairs, weekday "
    "calendars and date exceptions. Trips, stop times, shapes and agency "
    "rows are transient join inputs and are not stored."
)

# GTFS static route_type values 0-7, 11, 12 plus the extended HVT codes
# actually defined by the reference (not every integer in the gaps):
# https://developers.google.com/transit/gtfs/reference/extended-route-types
_VALID_ROUTE_TYPES = frozenset(
    {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        11,
        12,
        800,
        1000,
        1100,
        1200,
        1400,
        1700,
        1702,
    }
    | set(range(100, 118))
    | set(range(200, 210))
    | set(range(400, 406))
    | set(range(700, 717))
    | set(range(900, 907))
    | set(range(1300, 1308))
    | set(range(1500, 1508))
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


class _TooLarge(Exception):
    pass


# Bounded wait to reap a killed/cancelled transfer before reporting.
_TEARDOWN_SECONDS = 5.0


def _unlink_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def download_source(
    *,
    timeout_s: float = SOCKET_TIMEOUT_SECONDS,
    deadline_s: float = TOTAL_DOWNLOAD_DEADLINE_SECONDS,
    max_bytes: int | None = None,
    user_agent: str = USER_AGENT,
    source_url: str = SOURCE_URL,
) -> DownloadedFeed:
    """Fetch the fixed source into parent-owned temporary storage.

    The transfer runs in a child process performing one plain blocking
    fetch; the parent supervises it with the total deadline and kills it
    on expiry, which actually stops slow-drip and silent transfers instead
    of leaving I/O running. `source_url` is an internal seam for loopback
    tests only — production callers always use the fixed source, and the
    CLI offers no URL option. The temporary file is created and unlinked
    by the parent on every failure path; only success hands a path to the
    caller (the CLI deletes it afterwards). No retry loop. The size cap
    resolves at call time so tests can tighten it with monkeypatch.
    """
    import subprocess
    import sys

    if max_bytes is None:
        max_bytes = MAX_COMPRESSED_BYTES
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    handle = tempfile.NamedTemporaryFile(prefix="gtfs-", suffix=".zip", delete=False)
    handle.close()
    command = [
        sys.executable,
        "-m",
        "app.services.transit_fetch_child",
        "--url",
        source_url,
        "--out",
        handle.name,
        "--timeout",
        str(timeout_s),
        "--max-bytes",
        str(max_bytes),
        "--user-agent",
        user_agent,
    ]
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=backend_dir,
        )
    except OSError as exc:
        _unlink_quietly(handle.name)
        raise DownloadError(f"fetch failed: {exc}") from exc
    try:
        stdout, stderr = proc.communicate(timeout=deadline_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=_TEARDOWN_SECONDS)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        _unlink_quietly(handle.name)
        raise DownloadError("download deadline exceeded") from None
    if proc.returncode != 0:
        _unlink_quietly(handle.name)
        detail = (stderr or "").strip().splitlines()
        raise DownloadError(detail[-1][:200] if detail else "fetch failed")
    try:
        metadata = json.loads((stdout or "").strip().splitlines()[-1])
        digest = metadata["sha256"]
        last_modified = metadata.get("last_modified")
        etag = metadata.get("etag")
    except (IndexError, ValueError, KeyError, AttributeError) as exc:
        _unlink_quietly(handle.name)
        raise DownloadError(f"fetch failed: unreadable worker output: {exc}") from exc
    return DownloadedFeed(
        path=handle.name,
        content_sha256=digest,
        fetched_at=datetime.now(timezone.utc),
        source_last_modified=_parse_http_date(last_modified),
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


class _ByteBudget:
    """Shared cap over actually streamed uncompressed bytes."""

    def __init__(self, total_cap: int) -> None:
        self.used = 0
        self.cap = total_cap

    def add(self, count: int, what: str) -> None:
        self.used += count
        if self.used > self.cap:
            raise _fail(f"{what}: total uncompressed size exceeds limit")


def _open_member(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
):
    try:
        return archive.open(info)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise _fail(f"{info.filename!r}: cannot open member: {exc}") from exc


def _iter_member_lines(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    budget: _ByteBudget,
):
    """Yield decoded lines of one member, enforcing real byte counts.

    Central-directory sizes can lie, so every streamed byte is counted and
    closing the handle verifies the CRC. Errors anywhere — open, read,
    decode, CRC — become FeedError, never raw library exceptions.
    """
    import codecs

    name = info.filename
    handle = _open_member(archive, info)
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    pending = ""
    entry_total = 0
    exhausted = False
    try:
        while True:
            try:
                chunk = handle.read(CHUNK_BYTES)
            except (zipfile.BadZipFile, zlib.error, OSError, EOFError) as exc:
                raise _fail(f"{name}: corrupt data: {exc}") from exc
            if not chunk:
                break
            entry_total += len(chunk)
            if entry_total > MAX_ENTRY_BYTES:
                raise _fail(f"{name}: entry too large")
            budget.add(len(chunk), name)
            try:
                pending += decoder.decode(chunk)
            except UnicodeDecodeError as exc:
                raise _fail(f"{name}: invalid UTF-8") from exc
            *complete, pending = pending.split("\n")
            yield from complete
        try:
            pending += decoder.decode(b"", final=True)
        except UnicodeDecodeError as exc:
            raise _fail(f"{name}: invalid UTF-8") from exc
        if pending:
            yield pending
        exhausted = True
    finally:
        try:
            handle.close()
        except (zipfile.BadZipFile, zlib.error, OSError, EOFError) as exc:
            if exhausted:
                raise _fail(f"{name}: CRC check failed: {exc}") from exc


def _iter_records(
    archive: zipfile.ZipFile,
    name: str,
    required: frozenset[str],
    budget: _ByteBudget,
):
    """Yield ("headers", headers) then ("row", lineno, record) dicts.

    Strict CSV with duplicate/missing header checks; ragged rows, cell and
    row caps enforced per record. Header-only files yield headers alone.
    """
    infos = [info for info in archive.infolist() if info.filename == name]
    if not infos:
        raise _fail(f"missing file: {name}")
    lines = _iter_member_lines(archive, infos[0], budget)
    reader = csv.reader(lines, strict=True)
    try:
        headers = next(reader)
    except StopIteration:
        raise _fail(f"{name}: empty file") from None
    except csv.Error as exc:
        raise _fail(f"{name}: malformed CSV: {exc}") from exc
    missing = required - set(headers)
    if missing:
        raise _fail(f"{name}: missing headers: {', '.join(sorted(missing))}")
    if len(headers) != len(set(headers)):
        raise _fail(f"{name}: duplicate headers")
    yield "headers", headers
    lineno = 1
    try:
        for fields in reader:
            lineno += 1
            if len(fields) != len(headers):
                raise _fail(f"{name} line {lineno}: ragged row")
            for cell in fields:
                if len(cell.encode("utf-8")) > MAX_CELL_BYTES:
                    raise _fail(f"{name} line {lineno}: cell exceeds size limit")
            if lineno - 1 > MAX_ROWS_PER_FILE:
                raise _fail(f"{name}: too many rows")
            yield "row", lineno, dict(zip(headers, fields))
    except csv.Error as exc:
        raise _fail(f"{name}: malformed CSV: {exc}") from exc


def _read_rows(
    archive: zipfile.ZipFile,
    name: str,
    required: frozenset[str],
    budget: _ByteBudget,
) -> tuple[list[str], list[dict[str, str]]]:
    headers: list[str] = []
    rows: list[dict[str, str]] = []
    for kind, *payload in _iter_records(archive, name, required, budget):
        if kind == "headers":
            headers = payload[0]
        else:
            rows.append(payload[1])
    if not headers:
        raise _fail(f"{name}: empty file")
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
    budget = _ByteBudget(MAX_TOTAL_UNCOMPRESSED_BYTES)
    consumed = set(REQUIRED_FILES) | {"calendar.txt", "calendar_dates.txt"}
    with archive:
        _check_archive_members(archive)
        feed = ParsedFeed(agency_timezone="")
        _parse_agency(archive, feed, budget)
        _parse_stops(archive, feed, budget)
        _parse_routes(archive, feed, budget)
        _parse_trips(archive, feed, budget)
        _parse_stop_times(archive, feed, budget)
        _parse_calendars(archive, feed, budget)
        # Tolerated extras (shapes and friends) are still streamed within
        # the budget so their CRC is verified instead of trusted blindly.
        for info in archive.infolist():
            if info.is_dir() or info.filename in consumed:
                continue
            for _line in _iter_member_lines(archive, info, budget):
                pass
        _resolve_services(feed)
    return feed


def _check_len(value: str, limit: int, what: str) -> None:
    # Persisted columns are bounded; validate-only must not approve values
    # that fail only when written to PostgreSQL.
    if len(value.encode("utf-8")) > limit:
        raise _fail(f"{what}: value too long")


def _parse_agency(
    archive: zipfile.ZipFile, feed: ParsedFeed, budget: _ByteBudget
) -> None:
    _headers, rows = _read_rows(
        archive, "agency.txt", frozenset({"agency_timezone"}), budget
    )
    if not rows:
        raise _fail("agency.txt: no rows")
    zones = {row["agency_timezone"] for row in rows}
    if len(zones) != 1:
        raise _fail("agency.txt: ambiguous timezones")
    timezone_name = next(iter(zones))
    _check_len(timezone_name, 64, "agency.txt timezone")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise _fail(f"agency.txt: unknown timezone {timezone_name!r}") from exc
    feed.agency_timezone = timezone_name


def _parse_stops(
    archive: zipfile.ZipFile, feed: ParsedFeed, budget: _ByteBudget
) -> None:
    _headers, rows = _read_rows(
        archive,
        "stops.txt",
        frozenset({"stop_id", "stop_name", "stop_lat", "stop_lon"}),
        budget,
    )
    if not rows:
        raise _fail("stops.txt: no rows")
    for lineno, record in enumerate(rows, start=2):
        stop_id = record["stop_id"]
        if not stop_id:
            raise _fail(f"stops.txt line {lineno}: empty stop_id")
        if stop_id in feed.stops:
            raise _fail(f"stops.txt line {lineno}: duplicate stop_id")
        _check_len(stop_id, 64, f"stops.txt line {lineno} stop_id")
        latitude = _parse_float(record["stop_lat"], f"stops.txt line {lineno}")
        longitude = _parse_float(record["stop_lon"], f"stops.txt line {lineno}")
        if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
            raise _fail(f"stops.txt line {lineno}: coordinates out of bounds")
        if not record["stop_name"]:
            raise _fail(f"stops.txt line {lineno}: empty stop_name")
        _check_len(record["stop_name"], 255, f"stops.txt line {lineno} stop_name")
        stop_code = record.get("stop_code") or None
        if stop_code is not None:
            _check_len(stop_code, 64, f"stops.txt line {lineno} stop_code")
        parent = record.get("parent_station") or None
        if parent is not None:
            _check_len(parent, 64, f"stops.txt line {lineno} parent_station")
        location_type = record.get("location_type") or None
        if location_type is not None and location_type not in ("0", "1", "2", "3", "4"):
            raise _fail(f"stops.txt line {lineno}: invalid location_type")
        feed.stops[stop_id] = StopRow(
            stop_id=stop_id,
            stop_code=stop_code,
            stop_name=record["stop_name"],
            stop_lat=latitude,
            stop_lon=longitude,
            parent_station=parent,
            location_type=location_type,
        )
    for stop in feed.stops.values():
        if stop.parent_station is not None and stop.parent_station not in feed.stops:
            raise _fail(f"stops.txt: unknown parent_station {stop.parent_station!r}")


def _parse_routes(
    archive: zipfile.ZipFile, feed: ParsedFeed, budget: _ByteBudget
) -> None:
    _headers, rows = _read_rows(
        archive, "routes.txt", frozenset({"route_id", "route_type"}), budget
    )
    if not rows:
        raise _fail("routes.txt: no rows")
    for lineno, record in enumerate(rows, start=2):
        route_id = record["route_id"]
        if not route_id:
            raise _fail(f"routes.txt line {lineno}: empty route_id")
        if route_id in feed.routes:
            raise _fail(f"routes.txt line {lineno}: duplicate route_id")
        _check_len(route_id, 128, f"routes.txt line {lineno} route_id")
        route_type = _parse_route_type(record["route_type"])
        short_name = record.get("route_short_name") or None
        long_name = record.get("route_long_name") or None
        if short_name is not None:
            _check_len(short_name, 64, f"routes.txt line {lineno} short_name")
        if long_name is not None:
            _check_len(long_name, 255, f"routes.txt line {lineno} long_name")
        feed.routes[route_id] = RouteRow(
            route_id=route_id,
            short_name=short_name,
            long_name=long_name,
            route_type=route_type,
            mode=_derive_mode(route_type),
        )


def _parse_trips(
    archive: zipfile.ZipFile, feed: ParsedFeed, budget: _ByteBudget
) -> None:
    _headers, rows = _read_rows(
        archive, "trips.txt", frozenset({"route_id", "service_id", "trip_id"}), budget
    )
    if not rows:
        raise _fail("trips.txt: no rows")
    for lineno, record in enumerate(rows, start=2):
        trip_id = record["trip_id"]
        if not trip_id:
            raise _fail(f"trips.txt line {lineno}: empty trip_id")
        if trip_id in feed.trips:
            raise _fail(f"trips.txt line {lineno}: duplicate trip_id")
        if record["route_id"] not in feed.routes:
            raise _fail(f"trips.txt line {lineno}: unknown route_id")
        if not record["service_id"]:
            raise _fail(f"trips.txt line {lineno}: empty service_id")
        _check_len(record["service_id"], 128, f"trips.txt line {lineno} service_id")
        feed.trips[trip_id] = (record["route_id"], record["service_id"])


def _parse_stop_times(
    archive: zipfile.ZipFile, feed: ParsedFeed, budget: _ByteBudget
) -> None:
    required = frozenset(
        {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"}
    )
    infos = [info for info in archive.infolist() if info.filename == "stop_times.txt"]
    if not infos:
        raise _fail("missing file: stop_times.txt")
    lines = _iter_member_lines(archive, infos[0], budget)
    reader = csv.reader(lines, strict=True)
    try:
        headers = next(reader)
    except StopIteration:
        raise _fail("stop_times.txt: empty file") from None
    except csv.Error as exc:
        raise _fail(f"stop_times.txt: malformed CSV: {exc}") from exc
    missing = required - set(headers)
    if missing:
        raise _fail(f"stop_times.txt: missing headers: {', '.join(sorted(missing))}")
    if len(headers) != len(set(headers)):
        raise _fail("stop_times.txt: duplicate headers")
    index = {name: position for position, name in enumerate(headers)}
    sequences: dict[str, set[int]] = defaultdict(set)
    count = 0
    lineno = 1
    try:
        for fields in reader:
            lineno += 1
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
            if sequence < 0:
                raise _fail(
                    f"stop_times.txt line {lineno}: negative stop_sequence"
                )
            if sequence in sequences[trip_id]:
                raise _fail(f"stop_times.txt line {lineno}: duplicate stop_sequence")
            sequences[trip_id].add(sequence)
            for column in ("arrival_time", "departure_time"):
                _parse_gtfs_time(fields[index[column]], f"stop_times.txt line {lineno}")
            route_id, _service_id = feed.trips[trip_id]
            feed.stop_services.add((stop_id, route_id, feed.trips[trip_id][1]))
    except csv.Error as exc:
        raise _fail(f"stop_times.txt: malformed CSV: {exc}") from exc
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


def _parse_calendars(
    archive: zipfile.ZipFile, feed: ParsedFeed, budget: _ByteBudget
) -> None:
    names = set(archive.namelist())
    if "calendar.txt" in names:
        _headers, rows = _read_rows(
            archive,
            "calendar.txt",
            frozenset({"service_id", *_WEEKDAYS, "start_date", "end_date"}),
            budget,
        )
        for lineno, record in enumerate(rows, start=2):
            service_id = record["service_id"]
            if not service_id:
                raise _fail(f"calendar.txt line {lineno}: empty service_id")
            if service_id in feed.calendars:
                raise _fail(f"calendar.txt line {lineno}: duplicate service_id")
            _check_len(service_id, 128, f"calendar.txt line {lineno} service_id")
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
        _headers, rows = _read_rows(
            archive,
            "calendar_dates.txt",
            frozenset({"service_id", "date", "exception_type"}),
            budget,
        )
        seen: set[tuple[str, date]] = set()
        for lineno, record in enumerate(rows, start=2):
            if not record["service_id"]:
                raise _fail(f"calendar_dates.txt line {lineno}: empty service_id")
            _check_len(
                record["service_id"], 128, f"calendar_dates.txt line {lineno} service_id"
            )
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


# Upper bound for scanning one service band day by day; real bands span
# months, and anything wider is rejected as implausible rather than scanned.
_MAX_SERVICE_RANGE_DAYS = 3660


def _service_effective_span(
    feed: ParsedFeed,
    service_id: str,
    removed: set[date],
    added: list[date],
) -> tuple[date, date] | None:
    """First/last dates a referenced service actually runs, if any."""
    first: date | None = None
    last: date | None = None
    calendar = feed.calendars.get(service_id)
    if calendar is not None and any(calendar["flags"].values()):
        start, end = calendar["start_date"], calendar["end_date"]
        if (end - start).days > _MAX_SERVICE_RANGE_DAYS:
            raise _fail(f"implausible service range for {service_id!r}")
        day = start
        while day <= end:
            if calendar["flags"][_WEEKDAYS[day.weekday()]] and day not in removed:
                first = day
                break
            day += timedelta(days=1)
        if first is not None:
            day = end
            while day >= first:
                if calendar["flags"][_WEEKDAYS[day.weekday()]] and day not in removed:
                    last = day
                    break
                day -= timedelta(days=1)
    for day in added:
        if first is None or day < first:
            first = day
        if last is None or day > last:
            last = day
    if first is None or last is None:
        return None
    return first, last


def _resolve_services(feed: ParsedFeed) -> None:
    known_services = set(feed.calendars) | {
        service_id for service_id, _day, _kind in feed.exceptions
    }
    for trip_id, (_route_id, service_id) in feed.trips.items():
        if service_id not in known_services:
            raise _fail(f"trips.txt: unresolvable service_id for trip {trip_id!r}")
    removed: dict[str, set[date]] = defaultdict(set)
    added: dict[str, list[date]] = defaultdict(list)
    for service_id, day, kind in feed.exceptions:
        if kind == 1:
            added[service_id].append(day)
        else:
            removed[service_id].add(day)
    spans: list[tuple[date, date]] = []
    for service_id in {service for _route, service in feed.trips.values()}:
        span = _service_effective_span(
            feed, service_id, removed.get(service_id, set()), added.get(service_id, [])
        )
        if span is not None:
            spans.append(span)
    if not spans:
        raise _fail("no effective service dates")
    # The envelope is only the outer bounds of effective service; gaps
    # inside stay gaps, and routes_for_stop decides per actual date.
    feed.calendar_start = min(first for first, _last in spans)
    feed.calendar_end = max(last for _first, last in spans)
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


def _lock_state_row(session: Session) -> TransitState | None:
    """Return the singleton state row under a write lock, if it exists."""
    return session.scalar(
        select(TransitState).where(TransitState.id == 1).with_for_update()
    )


def _activate_generation(
    session: Session,
    staged_id: int,
    staged_fetched_at: datetime,
) -> str:
    """Flip the singleton pointer under a row lock with an age check.

    The check is unconditional: staged content older than the current
    activation never flips, no matter whether the worker was delayed
    before staging or during the transaction. Ties flip (last writer
    wins within one timestamp) and are documented as such. A first
    import has no row to protect; a concurrent first-import primary-key
    race surfaces as IntegrityError for the caller to map.
    """
    state = _lock_state_row(session)
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
    if current_active is not None and not as_aware_utc(
        staged_fetched_at
    ) >= as_aware_utc(current_active.fetched_at):
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
    _attempt: int = 0,
) -> ImportResult:
    """Stage one generation and flip the active pointer atomically.

    Download and parsing happen before this call, outside the transaction.
    Everything below commits once; any failure rolls the staging back and
    the previous pointer stays intact. An identical SHA only refreshes the
    check time of the actually active generation; a retained non-active
    generation with the same SHA is reported as superseded without touching
    its timestamps. A unique-constraint race (concurrent same-content
    imports, concurrent first imports) rolls back and retries once, then
    re-resolves against the winner.
    """
    existing = session.scalar(
        select(TransitFeed).where(TransitFeed.content_sha256 == content_sha256)
    )
    if existing is not None:
        # Resolve the active identity under the same synchronization as
        # activation: a concurrent flip between the lookup above and the
        # lock must not report an inactive feed as current, and a stale
        # concurrent recheck must never move checked_at backward.
        state = _lock_state_row(session)
        if state is None:
            session.rollback()
            return ImportResult(
                status="superseded",
                feed_id=None,
                content_sha256=content_sha256,
                counts=dict(feed.counts),
                warnings=[],
            )
        session.refresh(existing)
        if state.active_feed_id is not None and existing.id == state.active_feed_id:
            checked = as_aware_utc(existing.checked_at)
            candidate = as_aware_utc(checked_at)
            existing.checked_at = max(checked, candidate)
            session.commit()
            return ImportResult(
                status="already_current",
                feed_id=existing.id,
                content_sha256=content_sha256,
                counts=dict(feed.counts),
                warnings=[],
            )
        session.rollback()
        return ImportResult(
            status="superseded",
            feed_id=None,
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
    try:
        outcome = _activate_generation(session, staged.id, fetched_at)
    except IntegrityError:
        # Concurrent same-content import or first-import row race: roll back
        # and re-resolve once against whoever won.
        session.rollback()
        if _attempt > 0:
            raise
        return import_feed(
            session,
            feed,
            source_url=source_url,
            content_sha256=content_sha256,
            fetched_at=fetched_at,
            checked_at=checked_at,
            source_last_modified=source_last_modified,
            source_etag=source_etag,
            _attempt=_attempt + 1,
        )
    if outcome == "superseded":
        session.rollback()
        return ImportResult(
            status="superseded",
            feed_id=None,
            content_sha256=content_sha256,
            counts=dict(feed.counts),
            warnings=warnings,
        )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if _attempt > 0:
            raise
        return import_feed(
            session,
            feed,
            source_url=source_url,
            content_sha256=content_sha256,
            fetched_at=fetched_at,
            checked_at=checked_at,
            source_last_modified=source_last_modified,
            source_etag=source_etag,
            _attempt=_attempt + 1,
        )
    return ImportResult(
        status="activated",
        feed_id=staged.id,
        content_sha256=content_sha256,
        counts=dict(feed.counts),
        warnings=warnings,
    )
