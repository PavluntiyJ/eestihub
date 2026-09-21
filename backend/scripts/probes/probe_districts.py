"""Tallinn district boundary probe (ArcGIS REST, GeoJSON output).

Run from backend/:

    python -m scripts.probes.probe_districts

Verifies the public city GIS service behind gis.tallinn.ee: the two layers
(city districts and neighbourhoods), their feature counts and a GeoJSON
sample. The service currently answers without a token.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

from scripts.probes._http import fetch_json

SERVICE_URL = "https://gis.tallinn.ee/arcgis/rest/services/Linnaosad_asumid/MapServer"
LAYERS = {"Linnaosad": 1, "Asumid": 0}


def layer_info(layer_id: int) -> None:
    status, payload = fetch_json(f"{SERVICE_URL}/{layer_id}?f=json")
    if status != 200 or payload is None:
        print(f"  layer {layer_id}: HTTP {status}")
        return
    print(f"  layer {layer_id}: {payload.get('name')} ({payload.get('geometryType')})")
    fields = [field.get("name") for field in payload.get("fields", [])]
    print(f"    fields: {', '.join(fields[:12])}{'...' if len(fields) > 12 else ''}")


def feature_count(layer_id: int) -> int | None:
    query = urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    status, payload = fetch_json(f"{SERVICE_URL}/{layer_id}/query?{query}")
    return payload.get("count") if status == 200 and payload else None


def geojson_sample(layer_id: int) -> None:
    query = urlencode(
        {"where": "1=1", "outFields": "*", "f": "geojson", "resultRecordCount": "1"}
    )
    status, payload = fetch_json(f"{SERVICE_URL}/{layer_id}/query?{query}")
    if status != 200 or payload is None:
        print(f"  GeoJSON: HTTP {status}")
        return
    feature = payload["features"][0]
    geometry = feature["geometry"]
    properties = feature["properties"]
    print(f"  GeoJSON type: {payload['type']}, geometry: {geometry['type']}")
    print(f"  first feature: {properties.get('nimi')}, area {properties.get('pindala')}")
    ring_count = sum(len(polygon) for polygon in geometry["coordinates"])
    print(f"  first feature rings: {ring_count}")


def main() -> None:
    for name, layer_id in LAYERS.items():
        print(f"{name} (layer {layer_id}):")
        layer_info(layer_id)
        print(f"    features: {feature_count(layer_id)}")
        geojson_sample(layer_id)


if __name__ == "__main__":
    main()
