"""Basemap candidate probe for MapLibre.

Run from backend/:

    python -m scripts.probes.probe_basemap

Checks which public basemap endpoints answer without credentials, what they
return and whether CORS headers allow browser use. Terms of use are not
inferable from a 200 response; docs/DATA-SOURCES.md records the terms that
were read from each provider's documentation.
"""

from __future__ import annotations

from scripts.probes._http import fetch

# endpoint -> expected status without a key
TILE_CANDIDATES = {
    "OpenStreetMap": ("https://tile.openstreetmap.org/3/4/2.png", 200),
    "CARTO light": ("https://a.basemaps.cartocdn.com/light_all/3/4/2.png", 200),
    "Stadia alidade smooth": ("https://tiles.stadiamaps.com/tiles/alidade_smooth/3/4/2.png", 401),
}

STYLE_CANDIDATES = {
    "OpenFreeMap Liberty": ("https://tiles.openfreemap.org/styles/liberty", 200),
    "MapLibre demo": ("https://demotiles.maplibre.org/style.json", 200),
    "MapTiler streets": ("https://api.maptiler.com/maps/streets-v2/style.json", 403),
}

MAAAMET_WMS_CAPABILITIES = (
    "https://kaart.maaamet.ee/wms/alus?service=WMS&version=1.1.1&request=GetCapabilities"
)


def report(url: str, expected_status: int) -> bool:
    status, headers, body = fetch(url, timeout=30)
    lowered = {name.lower(): value for name, value in headers.items()}
    cors = lowered.get("access-control-allow-origin", "-")
    cache = lowered.get("cache-control", "-")
    content_type = lowered.get("content-type", "-")
    print(f"  HTTP {status} | {content_type} | {len(body)} bytes | CORS {cors} | {cache}")
    if status == 0:
        print(f"  {body.decode('utf-8', errors='replace')}")
    return status == expected_status


def main() -> None:
    failed = False

    print("raster tiles:")
    for name, (url, expected) in TILE_CANDIDATES.items():
        print(f"{name}: {url}")
        failed = not report(url, expected) or failed

    print("vector styles:")
    for name, (url, expected) in STYLE_CANDIDATES.items():
        print(f"{name}: {url}")
        failed = not report(url, expected) or failed

    print("Maa-amet WMS capabilities:")
    status, _, body = fetch(MAAAMET_WMS_CAPABILITIES, timeout=60)
    print(f"  HTTP {status} | {len(body)} bytes")
    if status != 200:
        failed = True
        print(f"  {body.decode('utf-8', errors='replace')}")
    for line in body.decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("<Name>") and stripped.endswith("</Name>"):
            name = stripped.removeprefix("<Name>").removesuffix("</Name>")
            if not name.startswith("default") and name not in {"OGC:WMS"}:
                print(f"  layer: {name}")

    if failed:
        raise SystemExit("one or more basemap probes returned an unexpected status")


if __name__ == "__main__":
    main()
