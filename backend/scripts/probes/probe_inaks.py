"""In-AKS address search and reverse geocoding probe.

Run from backend/:

    python -m scripts.probes.probe_inaks
    python -m scripts.probes.probe_inaks --address "Narva mnt 5"
    python -m scripts.probes.probe_inaks --reverse 543051.29 6588822.17

Coordinates are L-EST97 (EPSG:3301) for x/y input; responses also carry WGS84
viitepunkt_l (longitude) and viitepunkt_b (latitude). Reverse mode sends the
coordinates only -- combining them with an address is not supported.
"""

from __future__ import annotations

import argparse
import json
from urllib.parse import urlencode

from scripts.probes._http import fetch_json

GAZETTEER_URL = "https://aks.geoportaal.ee/inaks/inaadress/gazetteer"

DEFAULT_ADDRESS = "Tartu mnt 1"

BASE_PARAMS = {
    "results": "3",
    "appartment": "1",
    "unik": "0",
    "ky": "1",
    "iTappAsendus": "1",
}

ADDRESS_FIELDS = (
    "aadresstekst",
    "pikkaadress",
    "ads_oid",
    "adr_id",
    "adob_id",
    "tunnus",
    "koodaadress",
    "asum",
    "sihtnumber",
    "viitepunkt_x",
    "viitepunkt_y",
    "viitepunkt_l",
    "viitepunkt_b",
)


def request_params(address: str | None, reverse: tuple[str, str] | None) -> dict[str, str]:
    params = dict(BASE_PARAMS)

    if reverse is None and address is not None:
        params["address"] = address
    if reverse is not None:
        params["x"], params["y"] = reverse

    return params


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", default=None, help=f"default: {DEFAULT_ADDRESS!r}")
    parser.add_argument("--reverse", nargs=2, metavar=("X_LEST97", "Y_LEST97"))
    args = parser.parse_args()

    reverse = None if args.reverse is None else (args.reverse[0], args.reverse[1])
    address = None if reverse is not None else (args.address or DEFAULT_ADDRESS)
    url = f"{GAZETTEER_URL}?{urlencode(request_params(address, reverse))}"
    print(f"GET {url}")

    status, payload = fetch_json(url)
    print(f"HTTP {status}")

    if status != 200:
        raise SystemExit(f"unexpected HTTP status {status}")
    if payload is None or "addresses" not in payload:
        raise SystemExit("unexpected response shape: no 'addresses' key")

    addresses = payload["addresses"]
    print(f"matches: {len(addresses)}")
    if not addresses:
        raise SystemExit("the probe query returned no matches")

    print("first match:")
    print(json.dumps({key: addresses[0].get(key) for key in ADDRESS_FIELDS}, indent=2))


if __name__ == "__main__":
    main()
