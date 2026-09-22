"""Tests for GET /api/v1/addresses/search.

The provider transport is always mocked with minimal fixtures sourced from
real In-AKS responses (addresses, identifiers and coordinate shapes as
observed 2026-09-22); CI never touches the live gazetteer.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import main
from app.services import address_service
from app.services.address_service import (
    AddressProviderError,
    OutboundLimiter,
    SearchCache,
    search_addresses,
)


client = TestClient(main.app)

ENDPOINT = "/api/v1/addresses/search"


@pytest.fixture(autouse=True)
def _isolated_shared_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # The route uses the module-level shared cache/limiter; isolate them so
    # tests never observe each other's budget or cached responses.
    monkeypatch.setattr(address_service, "_DEFAULT_CACHE", SearchCache())
    monkeypatch.setattr(address_service, "_DEFAULT_LIMITER", OutboundLimiter())


def tallinn_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "aadresstekst": "Tartu mnt 1",
        "pikkaadress": "Harju maakond, Tallinn, Kesklinna linnaosa, Tartu mnt 1",
        "ads_oid": "EE04064863",
        "adr_id": "2249878",
        "adob_id": "10725273",
        "omavalitsus": "Tallinn",
        "maakond": "Harju maakond",
        "kvaliteet": "tapne_lahiaadress",
        "viitepunkt_l": "24.758626",
        "viitepunkt_b": "59.435048",
    }
    row.update(overrides)
    return row


def transport_with(payload: Any, status: int = 200, calls: list | None = None):
    def fake_transport(url: str, timeout_s: float, user_agent: str) -> tuple[int, bytes]:
        if calls is not None:
            calls.append(url)
        assert url.startswith("https://aks.geoportaal.ee/inaks/inaadress/gazetteer")
        assert "address=" in url and "results=8" in url
        assert timeout_s == 5.0
        assert user_agent
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return status, body

    return fake_transport


def service_search(query: str, **kwargs: Any):
    return search_addresses(
        query,
        cache=kwargs.pop("cache", SearchCache()),
        limiter=kwargs.pop("limiter", OutboundLimiter()),
        **kwargs,
    )


def test_exact_partial_unknown_quality_mapping() -> None:
    missing_quality = tallinn_row(ads_oid="EE5")
    del missing_quality["kvaliteet"]
    payload = {
        "addresses": [
            tallinn_row(ads_oid="EE1", kvaliteet="tapne_lahiaadress"),
            tallinn_row(ads_oid="EE2", kvaliteet="tapne_taisaadress"),
            tallinn_row(ads_oid="EE3", kvaliteet="osaline"),
            tallinn_row(ads_oid="EE4", kvaliteet="ligikaudne"),
            missing_quality,
        ],
        "host": "inaks-api-test",
    }
    response = service_search("Tartu mnt 1", transport=transport_with(payload))

    assert [candidate.quality for candidate in response.candidates] == [
        "exact",
        "exact",
        "partial",
        "unknown",
        "unknown",
    ]


def test_empty_addresses_array_is_successful_no_match() -> None:
    response = service_search(
        "zzz eiole sellist aadressi 99999",
        transport=transport_with({"addresses": []}),
    )

    assert response.query == "zzz eiole sellist aadressi 99999"
    assert response.candidates == []


def test_host_only_envelope_is_successful_no_match() -> None:
    response = service_search(
        "zzz eiole sellist aadressi 99999",
        transport=transport_with({"host": "inaks-api-test"}),
    )

    assert response.candidates == []


def test_arbitrary_json_is_provider_failure_not_no_match() -> None:
    for payload in ({"foo": 1}, ["addresses"], "addresses", 42, None):
        with pytest.raises(AddressProviderError) as exc_info:
            service_search("Tartu mnt 1", transport=transport_with(payload))
        assert exc_info.value.code == "address_provider_unavailable"


def test_out_of_area_rows_filter_normally() -> None:
    payload = {
        "addresses": [
            tallinn_row(),
            tallinn_row(
                ads_oid="EE00694633",
                aadresstekst="Mustamäe tee 5",
                pikkaadress="Pärnu maakond, Häädemeeste vald, Kabli küla, Mustamäe tee 5",
                omavalitsus="Häädemeeste vald",
            ),
        ],
        "host": "inaks-api-test",
    }
    response = service_search("Mustamäe tee 5", transport=transport_with(payload))

    assert [candidate.id for candidate in response.candidates] == ["EE04064863"]


def test_duplicate_ids_deduplicate_preserving_order() -> None:
    payload = {
        "addresses": [
            tallinn_row(ads_oid="EE1", aadresstekst="First"),
            tallinn_row(ads_oid="EE2", aadresstekst="Second"),
            tallinn_row(ads_oid="EE1", aadresstekst="First repeated"),
        ]
    }
    response = service_search("Tartu mnt 1", transport=transport_with(payload))

    assert [(c.id, c.short_label) for c in response.candidates] == [
        ("EE1", "First"),
        ("EE2", "Second"),
    ]


def test_string_coordinates_parse_to_numbers() -> None:
    response = service_search(
        "Tartu mnt 1", transport=transport_with({"addresses": [tallinn_row()]})
    )
    candidate = response.candidates[0]

    assert candidate.longitude == 24.758626
    assert candidate.latitude == 59.435048
    assert isinstance(candidate.longitude, float)


def test_invalid_coordinates_in_area_row_are_provider_failure() -> None:
    for bad in ("not-a-number", "NaN", "Infinity", None, True):
        payload = {"addresses": [tallinn_row(viitepunkt_l=bad)]}
        with pytest.raises(AddressProviderError) as exc_info:
            service_search("Tartu mnt 1", transport=transport_with(payload))
        assert exc_info.value.code == "address_provider_unavailable"


def test_out_of_bounds_coordinates_are_provider_failure() -> None:
    payload = {"addresses": [tallinn_row(viitepunkt_l="240.0", viitepunkt_b="95.0")]}
    with pytest.raises(AddressProviderError) as exc_info:
        service_search("Tartu mnt 1", transport=transport_with(payload))
    assert exc_info.value.code == "address_provider_unavailable"


def test_missing_id_or_labels_in_area_row_are_provider_failure() -> None:
    for row in (
        tallinn_row(ads_oid=""),
        tallinn_row(pikkaadress=""),
        tallinn_row(aadresstekst=None),
        "not-an-object",
        tallinn_row(omavalitsus="Missingville"),
    ):
        payload = {"addresses": [row]}
        if isinstance(row, dict) and row.get("omavalitsus") == "Missingville":
            response = service_search("Tartu mnt 1", transport=transport_with(payload))
            assert response.candidates == []
            continue
        with pytest.raises(AddressProviderError) as exc_info:
            service_search("Tartu mnt 1", transport=transport_with(payload))
        assert exc_info.value.code == "address_provider_unavailable"


def test_error_envelope_at_http_200_is_provider_failure() -> None:
    with pytest.raises(AddressProviderError) as exc_info:
        service_search(
            "Tartu mnt 1",
            transport=transport_with({"error": "overload", "host": "inaks-api-test"}),
        )
    assert exc_info.value.code == "address_provider_unavailable"


def test_non_200_status_is_provider_failure() -> None:
    calls: list = []
    with pytest.raises(AddressProviderError) as exc_info:
        service_search(
            "Tartu mnt 1",
            transport=transport_with({"addresses": []}, status=500, calls=calls),
        )
    assert exc_info.value.code == "address_provider_unavailable"
    assert len(calls) == 1


def test_timeout_calls_transport_exactly_once() -> None:
    calls: list = []

    def timeout_transport(url: str, timeout_s: float, user_agent: str):
        calls.append(url)
        raise TimeoutError("timed out")

    with pytest.raises(AddressProviderError) as exc_info:
        service_search("Tartu mnt 1", transport=timeout_transport)
    assert exc_info.value.code == "address_provider_unavailable"
    assert len(calls) == 1


def test_invalid_json_body_is_provider_failure() -> None:
    with pytest.raises(AddressProviderError) as exc_info:
        service_search("Tartu mnt 1", transport=transport_with(b"not json{{"))
    assert exc_info.value.code == "address_provider_unavailable"


def test_oversized_body_is_provider_failure() -> None:
    with pytest.raises(AddressProviderError) as exc_info:
        service_search(
            "Tartu mnt 1", transport=transport_with(b"x" * (1024 * 1024 + 100))
        )
    assert exc_info.value.code == "address_provider_unavailable"


def test_failures_are_not_cached() -> None:
    calls: list = []

    def flaky(url: str, timeout_s: float, user_agent: str):
        calls.append(url)
        if len(calls) == 1:
            raise TimeoutError("timed out")
        return 200, json.dumps({"addresses": []}).encode()

    cache = SearchCache()
    with pytest.raises(AddressProviderError):
        service_search("Tartu mnt 1", transport=flaky, cache=cache)
    assert service_search("Tartu mnt 1", transport=flaky, cache=cache).candidates == []
    assert len(calls) == 2


def test_successful_results_cache_by_query() -> None:
    calls: list = []
    cache = SearchCache()
    transport = transport_with({"addresses": [tallinn_row()]}, calls=calls)

    first = service_search("Tartu mnt 1", transport=transport, cache=cache)
    second = service_search("Tartu mnt 1", transport=transport, cache=cache)

    assert len(calls) == 1
    assert second == first


def test_cache_expiry_refetches() -> None:
    calls: list = []
    cache = SearchCache(ttl_seconds=0)
    transport = transport_with({"addresses": [tallinn_row()]}, calls=calls)

    service_search("Tartu mnt 1", transport=transport, cache=cache)
    service_search("Tartu mnt 1", transport=transport, cache=cache)

    assert len(calls) == 2


def test_cache_evicts_oldest_entry() -> None:
    calls: list = []
    cache = SearchCache(max_entries=1)
    transport = transport_with({"addresses": [tallinn_row()]}, calls=calls)

    service_search("first query here", transport=transport, cache=cache)
    service_search("second query here", transport=transport, cache=cache)
    service_search("first query here", transport=transport, cache=cache)

    assert len(calls) == 3


def test_rate_exhaustion_returns_busy() -> None:
    limiter = OutboundLimiter(max_calls=2, window_seconds=600.0)
    transport = transport_with({"addresses": []})

    service_search("first query here", transport=transport, limiter=limiter)
    service_search("second query here", transport=transport, limiter=limiter)
    with pytest.raises(AddressProviderError) as exc_info:
        service_search("third query here", transport=transport, limiter=limiter)

    assert exc_info.value.code == "address_search_busy"
    assert exc_info.value.retry_after is not None and exc_info.value.retry_after >= 1


def test_in_flight_limit_returns_busy() -> None:
    entered = threading.Event()
    release = threading.Event()
    calls: list = []

    def blocking_transport(url: str, timeout_s: float, user_agent: str):
        calls.append(url)
        entered.set()
        assert release.wait(timeout=10)
        return 200, json.dumps({"addresses": []}).encode()

    limiter = OutboundLimiter(max_in_flight=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            service_search,
            "first query here",
            transport=blocking_transport,
            cache=SearchCache(),
            limiter=limiter,
        )
        assert entered.wait(timeout=10)
        with pytest.raises(AddressProviderError) as exc_info:
            service_search(
                "second query here",
                transport=blocking_transport,
                cache=SearchCache(),
                limiter=limiter,
            )
        assert exc_info.value.code == "address_search_busy"
        release.set()
        assert first.result(timeout=10).candidates == []
    assert len(calls) == 1


def test_http_returns_exact_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []
    monkeypatch.setattr(
        address_service,
        "_fetch_upstream",
        transport_with({"addresses": [tallinn_row()], "host": "x"}, calls=calls),
    )
    response = client.get(ENDPOINT, params={"q": "Tartu mnt 1"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "query": "Tartu mnt 1",
        "candidates": [
            {
                "id": "EE04064863",
                "label": "Harju maakond, Tallinn, Kesklinna linnaosa, Tartu mnt 1",
                "short_label": "Tartu mnt 1",
                "longitude": 24.758626,
                "latitude": 59.435048,
                "district_id": None,
                "quality": "exact",
            }
        ],
        "attribution": {
            "provider": "maa_ja_ruumiamet",
            "label": "Maa- ja Ruumiamet / In-AKS",
            "source_url": "https://geoportaal.maaamet.ee/est/teenused/integreeritav-aadressiotsing-in-aks-p504.html",
        },
    }
    assert len(calls) == 1


def test_http_trims_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        address_service, "_fetch_upstream", transport_with({"addresses": []})
    )
    response = client.get(ENDPOINT, params={"q": "  Tartu mnt 1  "})

    assert response.status_code == 200
    assert response.json()["query"] == "Tartu mnt 1"


def test_http_busy_returns_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        address_service, "_DEFAULT_LIMITER", OutboundLimiter(max_calls=0)
    )
    monkeypatch.setattr(
        address_service,
        "_fetch_upstream",
        transport_with({"addresses": [tallinn_row()]}),
    )

    response = client.get(ENDPOINT, params={"q": "Tartu mnt 1"})

    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "address_search_busy"}}
    assert response.headers["cache-control"] == "no-store"
    assert int(response.headers["retry-after"]) >= 1


def test_http_provider_failure_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout_transport(url: str, timeout_s: float, user_agent: str):
        raise TimeoutError("timed out")

    monkeypatch.setattr(address_service, "_fetch_upstream", timeout_transport)

    response = client.get(ENDPOINT, params={"q": "Tartu mnt 1"})

    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "address_provider_unavailable"}}
    assert response.headers["cache-control"] == "no-store"
    assert "retry-after" not in response.headers


@pytest.mark.parametrize("query", ["ab", "a" * 201, "ab\x00c", "ab\nc", "   "])
def test_http_invalid_queries_return_422_without_provider_call(
    monkeypatch: pytest.MonkeyPatch, query: str
) -> None:
    calls: list = []
    monkeypatch.setattr(
        address_service, "_fetch_upstream", transport_with({}, calls=calls)
    )

    response = client.get(ENDPOINT, params={"q": query})

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert calls == []


def test_http_missing_query_returns_422_with_no_store() -> None:
    response = client.get(ENDPOINT)

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"


def test_http_repeated_query_returns_422_with_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list = []
    monkeypatch.setattr(
        address_service, "_fetch_upstream", transport_with({}, calls=calls)
    )

    response = client.get(ENDPOINT, params=[("q", "Tartu mnt 1"), ("q", "Tartu mnt 1")])

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert calls == []


def test_http_padded_max_length_query_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        address_service, "_fetch_upstream", transport_with({"addresses": []})
    )

    response = client.get(ENDPOINT, params={"q": "  " + "e" * 200 + "  "})

    assert response.status_code == 200
    assert response.json()["query"] == "e" * 200


@pytest.mark.parametrize(
    "payload",
    [
        {"addresses": [{"x": 1}], "unexpected": True},
        {"addresses": None, "host": "inaks-api-test"},
        {"host": None},
        {"host": "inaks-api-test", "unexpected": True},
        {"host": ""},
        {"addresses": [], "host": "inaks-api-test", "unexpected": True},
    ],
)
def test_http_strict_envelope_failures_return_503(
    monkeypatch: pytest.MonkeyPatch, payload: Any
) -> None:
    monkeypatch.setattr(address_service, "_fetch_upstream", transport_with(payload))

    response = client.get(ENDPOINT, params={"q": "Tartu mnt 1"})

    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "address_provider_unavailable"}}


@pytest.mark.parametrize(
    "row_overrides",
    [
        {"kvaliteet": []},
        {"kvaliteet": {}},
        {"viitepunkt_l": 10**400},
        {"viitepunkt_b": "1e400"},
    ],
)
def test_http_malformed_rows_return_json_safe_503(
    monkeypatch: pytest.MonkeyPatch, row_overrides: dict
) -> None:
    monkeypatch.setattr(
        address_service,
        "_fetch_upstream",
        transport_with({"addresses": [tallinn_row(**row_overrides)]}),
    )

    response = client.get(ENDPOINT, params={"q": "Tartu mnt 1"})

    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "address_provider_unavailable"}}


def test_http_failure_then_success_is_not_negatively_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list = []

    def flaky(url: str, timeout_s: float, user_agent: str):
        calls.append(url)
        if len(calls) == 1:
            raise TimeoutError("timed out")
        return 200, json.dumps({"addresses": []}).encode()

    monkeypatch.setattr(address_service, "_fetch_upstream", flaky)

    assert client.get(ENDPOINT, params={"q": "Tartu mnt 1"}).status_code == 503
    failing = client.get(ENDPOINT, params={"q": "Tartu mnt 1"})
    assert failing.status_code == 200
    assert failing.json()["candidates"] == []
    assert len(calls) == 2
