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
) -> tuple[int, dict[str, str], bytes]:
    """Return (status, headers, body) and never raise for HTTP error codes."""

    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("User-Agent", USER_AGENT)
    for name, value in (headers or {}).items():
        request.add_header(name, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()


def fetch_json(url: str, **kwargs: Any) -> tuple[int, Any]:
    status, _, body = fetch(url, **kwargs)

    try:
        return status, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None
