"""Internal download worker for the GTFS import. Do not invoke directly.

Parent supervision lives in transit_import.download_source, which always
kills this process on deadline expiry and owns the temporary file. This
module performs one plain blocking fetch with a fixed per-operation socket
timeout and a size cap; it has no deadline of its own and never retries.
"""

import argparse
import hashlib
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CHUNK_BYTES = 65536


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", required=True, type=float)
    parser.add_argument("--max-bytes", required=True, type=int)
    parser.add_argument("--user-agent", required=True)
    args = parser.parse_args(argv)
    request = Request(args.url, headers={"User-Agent": args.user_agent})
    try:
        response = urlopen(request, timeout=args.timeout)
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"error: fetch failed: {exc}", file=sys.stderr)
        return 2
    if response.status != 200:
        print(f"error: unexpected HTTP status {response.status}", file=sys.stderr)
        return 2
    digest = hashlib.sha256()
    total = 0
    try:
        with open(args.out, "wb") as handle:
            while True:
                chunk = response.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > args.max_bytes:
                    print(
                        f"error: archive exceeds {args.max_bytes} bytes",
                        file=sys.stderr,
                    )
                    return 2
                digest.update(chunk)
                handle.write(chunk)
    except (TimeoutError, OSError) as exc:
        print(f"error: stalled download: {exc}", file=sys.stderr)
        return 2
    finally:
        try:
            response.close()
        except Exception:  # noqa: BLE001 (teardown only)
            pass
    print(
        json.dumps(
            {
                "sha256": digest.hexdigest(),
                "bytes": total,
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
