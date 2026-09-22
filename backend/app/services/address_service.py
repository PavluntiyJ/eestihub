"""Tallinn address search over the In-AKS gazetteer.

Read-only adapter with no database, no persistence and no retry/fallback:
exactly one upstream call per cache miss. Validation of the public ``q``
parameter lives in the route; this module assumes a trimmed query.
"""

from __future__ import annotations

import json
import threading
import time
import unicodedata
from collections import OrderedDict, deque
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.schemas.addresses import (
    AddressAttribution,
    AddressCandidate,
    AddressSearchResponse,
)

UPSTREAM_URL = "https://aks.geoportaal.ee/inaks/inaadress/gazetteer"
UPSTREAM_PARAMS = {
    "results": "8",
    "appartment": "1",
    "unik": "0",
    "ky": "1",
    "iTappAsendus": "1",
}
REQUEST_TIMEOUT_SECONDS = 5.0
MAX_BODY_BYTES = 1024 * 1024
MAX_CANDIDATES = 8
CACHE_TTL_SECONDS = 60.0
CACHE_MAX_ENTRIES = 256
# Conservative application bounds, well inside the provider's per-IP limits.
# They assume one process per egress IP; scale-out needs a shared quota.
LIMITER_MAX_CALLS = 1000
LIMITER_WINDOW_SECONDS = 600.0
LIMITER_MAX_IN_FLIGHT = 4

ATTRIBUTION = AddressAttribution(
    provider="maa_ja_ruumiamet",
    label="Maa- ja Ruumiamet / In-AKS",
    source_url="https://geoportaal.maaamet.ee/est/teenused/integreeritav-aadressiotsing-in-aks-p504.html",
)

_EXACT_QUALITIES = frozenset({"tapne_lahiaadress", "tapne_taisaadress"})

Transport = Callable[[str, float, str], tuple[int, bytes]]


class AddressProviderError(Exception):
    """Upstream or local-budget failure, mapped to 503 by the route."""

    def __init__(self, code: str, retry_after: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


class _InvalidRow(Exception):
    """A required field is missing or unusable in an in-area provider row."""


def has_controls(value: str) -> bool:
    return any(unicodedata.category(char) == "Cc" for char in value)


class SearchCache:
    """Thread-safe TTL cache with oldest-first eviction. Successes only."""

    def __init__(
        self,
        ttl_seconds: float = CACHE_TTL_SECONDS,
        max_entries: int = CACHE_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._items: OrderedDict[str, tuple[float, AddressSearchResponse]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> AddressSearchResponse | None:
        with self._lock:
            hit = self._items.get(key)
            if hit is None:
                return None
            stored_at, response = hit
            if self._clock() - stored_at >= self._ttl:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return response

    def put(self, key: str, response: AddressSearchResponse) -> None:
        with self._lock:
            self._items[key] = (self._clock(), response)
            self._items.move_to_end(key)
            while len(self._items) > self._max_entries:
                self._items.popitem(last=False)


class OutboundLimiter:
    """Thread-safe rolling-window rate limiter plus in-flight semaphore."""

    def __init__(
        self,
        max_calls: int = LIMITER_MAX_CALLS,
        window_seconds: float = LIMITER_WINDOW_SECONDS,
        max_in_flight: int = LIMITER_MAX_IN_FLIGHT,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._clock = clock
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()
        self._in_flight = threading.Semaphore(max_in_flight)

    def acquire_rate(self) -> int | None:
        """Consume one budget slot; return Retry-After seconds when exhausted."""
        now = self._clock()
        with self._lock:
            while self._calls and self._calls[0] <= now - self._window:
                self._calls.popleft()
            if len(self._calls) >= self._max_calls:
                if self._calls:
                    retry_after = self._calls[0] + self._window - now
                else:
                    retry_after = self._window
                return max(1, int(retry_after) + (1 if retry_after % 1 else 0))
            self._calls.append(now)
            return None

    def acquire_flight(self) -> bool:
        return self._in_flight.acquire(blocking=False)

    def release_flight(self) -> None:
        self._in_flight.release()


_DEFAULT_CACHE = SearchCache()
_DEFAULT_LIMITER = OutboundLimiter()


def _fetch_upstream(url: str, timeout_s: float, user_agent: str) -> tuple[int, bytes]:
    # Note on the five-second bound: urllib applies the timeout to each
    # blocking socket operation (connect and every read — i.e. inactivity),
    # not to the total operation. A strict total deadline would need an
    # async client or a worker thread, both outside this stdlib-only sync
    # adapter. In practice the total stays small: responses observed
    # at ~0.3s, bodies are capped at 1 MiB, and the browser additionally
    # aborts silently-hanging calls with its own finite timeout.
    request = Request(
        url, headers={"User-Agent": user_agent, "Accept": "application/json"}
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            status = response.status
            body = response.read(MAX_BODY_BYTES + 1)
    except HTTPError as exc:
        raise AddressProviderError("address_provider_unavailable") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise AddressProviderError("address_provider_unavailable") from exc
    if len(body) > MAX_BODY_BYTES:
        raise AddressProviderError("address_provider_unavailable")
    return status, body


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        try:
            number = float(value)
        except OverflowError:
            # 10**400 and friends: not a usable coordinate, never a 500.
            return None
    elif isinstance(value, float):
        number = value
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _match_quality(value: object) -> str:
    # Only exact string codes map; lists, dicts, numbers and anything else
    # stay unknown instead of raising TypeError in set membership.
    if not isinstance(value, str):
        return "unknown"
    if value in _EXACT_QUALITIES:
        return "exact"
    if value == "osaline":
        return "partial"
    return "unknown"


def _candidate_from_row(row: object) -> AddressCandidate | None:
    if not isinstance(row, dict):
        raise _InvalidRow("row is not an object")
    identifier = row.get("ads_oid")
    label = row.get("pikkaadress")
    short_label = row.get("aadresstekst")
    longitude = _finite_number(row.get("viitepunkt_l"))
    latitude = _finite_number(row.get("viitepunkt_b"))
    if (
        not isinstance(identifier, str)
        or not identifier
        or not isinstance(label, str)
        or not label
        or not isinstance(short_label, str)
        or not short_label
        or longitude is None
        or latitude is None
        or not -180.0 <= longitude <= 180.0
        or not -90.0 <= latitude <= 90.0
    ):
        raise _InvalidRow("in-area row misses required fields")
    if row.get("omavalitsus") != "Tallinn":
        return None
    # A missing quality stays unknown; a present non-string quality is a
    # malformed row rather than an unrecognized code.
    if "kvaliteet" in row:
        if not isinstance(row["kvaliteet"], str):
            raise _InvalidRow("non-string match quality")
        quality = _match_quality(row["kvaliteet"])
    else:
        quality = "unknown"
    return AddressCandidate(
        id=identifier,
        label=label,
        short_label=short_label,
        longitude=longitude,
        latitude=latitude,
        district_id=None,
        quality=quality,  # type: ignore[arg-type]
    )


def _response_from_payload(payload: Any, query: str) -> AddressSearchResponse:
    if not isinstance(payload, dict):
        raise AddressProviderError("address_provider_unavailable")
    if "error" in payload:
        raise AddressProviderError("address_provider_unavailable")
    # Only the documented envelope shape is accepted: extra keys mean the
    # provider changed its contract, which is a failure, not a silent pass.
    if any(key not in ("addresses", "host") for key in payload):
        raise AddressProviderError("address_provider_unavailable")
    addresses = payload.get("addresses")
    if addresses is None:
        # A missing addresses key in a valid host-only envelope is the
        # provider's no-match shape. Explicit null is a schema failure;
        # the upfront key check already rejected anything but host here.
        if "addresses" not in payload and set(payload) == {"host"}:
            host = payload["host"]
            if isinstance(host, str) and host:
                return AddressSearchResponse(
                    query=query, candidates=[], attribution=ATTRIBUTION
                )
        raise AddressProviderError("address_provider_unavailable")
    if not isinstance(addresses, list):
        raise AddressProviderError("address_provider_unavailable")
    candidates: list[AddressCandidate] = []
    seen: set[str] = set()
    for row in addresses:
        candidate = _candidate_from_row(row)
        if candidate is None:
            continue
        if candidate.id in seen:
            continue
        seen.add(candidate.id)
        candidates.append(candidate)
    return AddressSearchResponse(
        query=query,
        candidates=candidates[:MAX_CANDIDATES],
        attribution=ATTRIBUTION,
    )


def search_addresses(
    query: str,
    *,
    transport: Transport | None = None,
    cache: SearchCache | None = None,
    limiter: OutboundLimiter | None = None,
    user_agent: str | None = None,
) -> AddressSearchResponse:
    # Defaults resolve from module globals at call time so tests can
    # monkeypatch the shared instances for HTTP-level cases.
    if transport is None:
        transport = _fetch_upstream
    if cache is None:
        cache = _DEFAULT_CACHE
    if limiter is None:
        limiter = _DEFAULT_LIMITER
    cached = cache.get(query)
    if cached is not None:
        return cached
    if not limiter.acquire_flight():
        raise AddressProviderError("address_search_busy", 1)
    try:
        retry_after = limiter.acquire_rate()
        if retry_after is not None:
            raise AddressProviderError("address_search_busy", retry_after)
        params = dict(UPSTREAM_PARAMS)
        params["address"] = query
        url = f"{UPSTREAM_URL}?{urlencode(params)}"
        agent = user_agent or get_settings().address_search_user_agent
        try:
            status, body = transport(url, REQUEST_TIMEOUT_SECONDS, agent)
        except AddressProviderError:
            raise
        except Exception as exc:
            # Any transport failure is provider unavailability, never a 500:
            # there is exactly one upstream attempt, no retry or fallback.
            raise AddressProviderError("address_provider_unavailable") from exc
        if status != 200:
            raise AddressProviderError("address_provider_unavailable")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AddressProviderError("address_provider_unavailable") from exc
        try:
            response = _response_from_payload(payload, query)
        except _InvalidRow as exc:
            raise AddressProviderError("address_provider_unavailable") from exc
    finally:
        limiter.release_flight()
    cache.put(query, response)
    return response
