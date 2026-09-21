"""Minimal stdlib HTTP helper shared by the M02 data-source probes.

The probes intentionally avoid third-party dependencies so any checkout can
run them:

    cd backend
    python -m scripts.probes.probe_inaks

Every probe prints what it requested, what came back and which parts of the
answer were verified, so a reviewer can re-run them and compare with
docs/DATA-SOURCES.md.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "EestiHub-data-source-probe/0.1 (+https://github.com/PavluntiyJ/eestihub)"


def fetch(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 1,
) -> tuple[int, dict[str, str], bytes]:
    """Return (status, headers, body); HTTP and network errors become status 0.

    A network error is retried once, because public providers occasionally
    drop a connection or answer slowly.
    """

    last_result: tuple[int, dict[str, str], bytes] = (0, {}, b"")

    for attempt in range(retries + 1):
        last_result = _fetch_once(url, method=method, body=body, headers=headers, timeout=timeout)
        if last_result[0] != 0 or attempt == retries:
            break
        time.sleep(1)

    return last_result


def _fetch_once(
    url: str,
    *,
    method: str,
    body: bytes | None,
    headers: dict[str, str] | None,
    timeout: int,
) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("User-Agent", USER_AGENT)
    for name, value in (headers or {}).items():
        request.add_header(name, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        reason = getattr(error, "reason", error)
        return 0, {}, f"network error: {reason}".encode("utf-8")


def fetch_json(url: str, **kwargs: Any) -> tuple[int, Any]:
    status, _, body = fetch(url, **kwargs)

    try:
        return status, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None
