"""Import a versioned Tallinn GTFS snapshot: download, validate, stage, activate.

Run from backend/:

    python -m scripts.import_gtfs
    python -m scripts.import_gtfs --validate-only
    python -m scripts.import_gtfs --file /tmp/gtfs.zip [--last-modified "..." --etag "..."]

Exit codes: 0 success (including already-current and superseded), 1 invalid
feed, 2 download/HTTP failure, 3 database lock conflict, 4 transaction error.
Only concise counts and reasons are printed, never credentials or records.
No download happens on API startup or HTTP reads; there is no automation.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.core.db import SessionLocal, engine
from app.models import Base
from app.models import transit as _transit_models  # noqa: F401  (table registration)
from app.services.transit_import import (
    SOURCE_URL,
    DownloadError,
    FeedError,
    ImportResult,
    ParsedFeed,
    download_source,
    import_feed,
    parse_feed,
    prepare_local_file,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        default=None,
        help="import from a local archive instead of downloading",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="run all archive/data checks without database writes",
    )
    parser.add_argument(
        "--last-modified",
        default=None,
        help="source Last-Modified for --file (HTTP date); otherwise unknown",
    )
    parser.add_argument(
        "--etag",
        default=None,
        help="source ETag for --file; otherwise unknown",
    )
    args = parser.parse_args(argv)
    if (args.last_modified is not None or args.etag is not None) and args.file is None:
        parser.error("--last-modified/--etag require --file")
    return args


def _summarize(feed: ParsedFeed, sha256: str) -> str:
    counts = feed.counts
    return (
        f"stops={counts.get('stops', 0)} "
        f"routes={counts.get('routes', 0)} "
        f"trips={counts.get('trips', 0)} "
        f"stop_times={counts.get('stop_times', 0)} "
        f"stop_services={counts.get('stop_services', 0)} "
        f"sha256={sha256[:12]}"
    )


def _report_result(result: ImportResult) -> None:
    counts = result.counts
    print(
        f"{result.status}: stops={counts.get('stops', 0)} "
        f"routes={counts.get('routes', 0)} "
        f"trips={counts.get('trips', 0)} "
        f"stop_services={counts.get('stop_services', 0)}"
    )
    for warning in result.warnings:
        print(warning)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    downloaded_path: str | None = None
    if args.file is not None:
        try:
            local = prepare_local_file(
                args.file, last_modified=args.last_modified, etag=args.etag
            )
        except FeedError as exc:
            print(f"error: invalid feed: {exc}")
            return 1
        path = local.path
        content_sha256 = local.content_sha256
        fetched_at = local.fetched_at
        source_last_modified = local.source_last_modified
        source_etag = local.source_etag
    else:
        try:
            downloaded = download_source()
        except DownloadError as exc:
            print(f"error: download failed: {exc}")
            return 2
        path = downloaded.path
        downloaded_path = downloaded.path
        content_sha256 = downloaded.content_sha256
        fetched_at = downloaded.fetched_at
        source_last_modified = downloaded.source_last_modified
        source_etag = downloaded.source_etag
    try:
        try:
            feed = parse_feed(path)
        except FeedError as exc:
            print(f"error: invalid feed: {exc}")
            return 1
        print(f"validated: {_summarize(feed, content_sha256)}")
        if args.validate_only:
            return 0
        Base.metadata.create_all(bind=engine)
        checked_at = datetime.now(timezone.utc)
        with SessionLocal() as session:
            result = import_feed(
                session,
                feed,
                source_url=SOURCE_URL,
                content_sha256=content_sha256,
                fetched_at=fetched_at,
                checked_at=checked_at,
                source_last_modified=source_last_modified,
                source_etag=source_etag,
            )
        _report_result(result)
        return 0
    except OperationalError as exc:
        print(f"error: database lock conflict: {exc}")
        return 3
    except (IntegrityError, SQLAlchemyError) as exc:
        print(f"error: transaction failed: {exc}")
        return 4
    finally:
        if downloaded_path is not None:
            try:
                os.unlink(downloaded_path)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
