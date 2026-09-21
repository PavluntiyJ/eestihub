"""Tallinn district boundary probe (ArcGIS REST, GeoJSON output).

Run from backend/:

    python -m scripts.probes.probe_districts

Verifies the public city GIS service behind gis.tallinn.ee: the two layers
(city districts and neighbourhoods), their feature counts and a GeoJSON
sample. The service currently answers without a token.
"""

from __future__ import annotations

from urllib.parse import urlencode

from scripts.probes._http import fetch_json

SERVICE_URL = "https://gis.tallinn.ee/arcgis/rest/services/Linnaosad_asumid/MapServer"

# layer 1 names features with "nimi", layer 0 (neighbourhoods) with "asumi_nimi".
LAYERS = {
    "Linnaosad": {"id": 1, "name_field": "nimi"},
    "Asumid": {"id": 0, "name_field": "asumi_nimi"},
}


def layer_info(layer_id: int) -> bool:
    status, payload = fetch_json(f"{SERVICE_URL}/{layer_id}?f=json", timeout=60)
    if status != 200 or payload is None:
        print(f"  layer {layer_id}: HTTP {status}")
        return False

    print(f"  layer {layer_id}: {payload.get('name')} ({payload.get('geometryType')})")
    fields = [field.get("name") for field in payload.get("fields", [])]
    print(f"    fields: {', '.join(fields[:12])}{'...' if len(fields) > 12 else ''}")
    return True


def feature_count(layer_id: int) -> int | None:
    query = urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    status, payload = fetch_json(f"{SERVICE_URL}/{layer_id}/query?{query}", timeout=60)
    return payload.get("count") if status == 200 and payload else None


def ring_count(geometry: dict) -> int | None:
    geometry_type = geometry["type"]
    if geometry_type == "MultiPolygon":
        return sum(len(polygon) for polygon in geometry["coordinates"])
    if geometry_type == "Polygon":
        return len(geometry["coordinates"])
    return None


def geojson_sample(layer_id: int, name_field: str) -> bool:
    query = urlencode(
        {"where": "1=1", "outFields": "*", "f": "geojson", "resultRecordCount": "1"}
    )
    status, payload = fetch_json(f"{SERVICE_URL}/{layer_id}/query?{query}", timeout=60)
    if status != 200 or payload is None or not payload.get("features"):
        print(f"  GeoJSON: HTTP {status}")
        return False

    feature = payload["features"][0]
    geometry = feature["geometry"]
    properties = feature["properties"]
    print(f"  GeoJSON type: {payload['type']}, geometry: {geometry['type']}")
    print(
        f"  first feature: {properties.get(name_field)}, area {properties.get('pindala')}"
    )
    print(f"  first feature rings: {ring_count(geometry)}")
    return True


def main() -> None:
    failed = False

    for name, layer in LAYERS.items():
        print(f"{name} (layer {layer['id']}):")
        failed = not layer_info(layer["id"]) or failed

        count = feature_count(layer["id"])
        print(f"    features: {count}")
        failed = count is None or failed

        failed = not geojson_sample(layer["id"], layer["name_field"]) or failed

    if failed:
        raise SystemExit("one or more district probes failed")


if __name__ == "__main__":
    main()
