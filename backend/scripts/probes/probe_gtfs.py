"""Tallinn GTFS feed probe.

Run from backend/:

    python -m scripts.probes.probe_gtfs

Downloads the zip into memory, reports the HTTP metadata and inspects the
archive: entry sizes, row counts and the agency row. The feed is ~2.5 MB, so
this stays a single request.
"""

from __future__ import annotations

import csv
import io
import zipfile

from scripts.probes._http import fetch

GTFS_URL = "https://transport.tallinn.ee/data/gtfs.zip"

EXPECTED_ENTRIES = {
    "agency.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "routes.txt",
    "shapes.txt",
    "stops.txt",
    "stop_times.txt",
    "trips.txt",
}


def row_count(archive: zipfile.ZipFile, name: str) -> int:
    with archive.open(name) as handle:
        return sum(1 for _ in io.TextIOWrapper(handle, encoding="utf-8-sig"))


def sample(archive: zipfile.ZipFile, name: str, limit: int = 3) -> list[list[str]]:
    with archive.open(name) as handle:
        reader = csv.reader(io.TextIOWrapper(handle, encoding="utf-8-sig"))
        return [row for _, row in zip(range(limit), reader)]


def main() -> None:
    status, headers, body = fetch(GTFS_URL, timeout=120)
    print(f"HEAD/GET {GTFS_URL}")
    print(f"HTTP {status}")
    for header in ("Content-Type", "Content-Length", "Last-Modified", "ETag"):
        if header in headers:
            print(f"{header}: {headers[header]}")

    if status != 200:
        raise SystemExit(f"unexpected HTTP status {status}")

    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile as error:
        raise SystemExit(f"response is not a zip archive: {error}") from error

    with archive:
        missing = EXPECTED_ENTRIES - set(archive.namelist())
        if missing:
            raise SystemExit(f"feed is missing expected entries: {', '.join(sorted(missing))}")

        print("entries (uncompressed rows):")
        for name in sorted(archive.namelist()):
            print(f"  {name:<24} {row_count(archive, name):>8}")
        print("agency.txt:")
        for row in sample(archive, "agency.txt"):
            print(f"  {row}")
        print("routes.txt (first 3):")
        for row in sample(archive, "routes.txt"):
            print(f"  {row}")


if __name__ == "__main__":
    main()
