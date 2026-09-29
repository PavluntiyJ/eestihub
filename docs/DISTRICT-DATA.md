# District data and boundary operations

## Official boundaries

The checked-in `backend/app/data/districts.geojson` contains the eight Tallinn
districts from the national EHAK settlement-unit SHP export, dated **2026-09-02**,
retrieved **2026-09-29**. It is served without a live provider request.

- [Official dataset page](https://geoportaal.maaruum.ee/est/ruumiandmed/haldus-ja-asustusjaotus-p119.html)
- [Monthly SHP distribution](https://s3.pilw.io/rp-kemit-kataster/EHAK/asustusyksus_shp.zip)
- [Reuse terms](https://kataster.ee/sites/default/files/documents/2024-03/MTP_andmeteenuste_kasutustingimused.pdf)

The dataset page requires attribution to Maa- ja Ruumiamet with the data date.
The linked terms permit commercial/non-commercial use and redistribution
(sections 1.4–1.5 and 2.5). This source replaces the earlier unverified Tallinn
city GIS candidate; no city GIS geometry was used. These data terms are separate
from the repository's MIT code license. Attribution is visible below the map
and is included in the API's GeoJSON metadata alongside source/license links,
retrieval date and the original ZIP SHA-256.

Selection: `OKOOD=0784` (Tallinn), `TYYP=6` (district); application IDs map from
official EHAK codes. Original polygons/multipolygons and holes are retained,
including Aegna in Kesklinn. Coordinates are transformed from EPSG:3301 to
EPSG:4326 longitude/latitude and rounded to six decimals. No geometric
simplification or reconstructed approximate district boundaries are used.
The representative points in the rent response are legacy display coordinates,
not official computed polygon centroids. Address search still returns
`district_id: null`; the release does not claim point-in-polygon matching.

To refresh, download the official distribution to a temporary file, inspect its
export date, and use a maintenance environment with `pyshp==3.1.6` and
`pyproj==3.8.0` (neither is a runtime dependency):

```bash
cd backend
python -m scripts.build_district_boundaries /path/to/asustusyksus_shp.zip
python -m pytest tests/test_districts.py
```

Update the script's snapshot/retrieval labels and the visible map credit when
refreshing. Review the diff, coverage, coordinate bounds and terms before
committing the artifact. The source ZIP and conversion dependencies are not
shipped. Failure to refresh leaves the last reviewed artifact intact.

## Rent provenance

`GET /api/v1/planner/districts?rooms=1` accepts total rooms 1/2/3. It returns all
eight stable IDs, ordered by rent then name, with missing rent last. Each row
has its own observation date, source URL, `published_aggregate`,
`legacy_estimate` or `unknown` basis, and freshness. A published observation
within 90 days is `current`; older observations are `stale`. Legacy data has
`unknown` freshness regardless of its seed date. Missing data stays null;
an empty/unavailable database returns 503 instead of fabricated current prices.

The published figures are manually transcribed range midpoints, not a live
listing feed or measured arithmetic averages. See
[the original rent source and transformation](../backend/scripts/data/SOURCES.md).
The 2026-05-27 report is stale at this release date and the UI says so.

Legacy utilities are separate, non-seasonal planning assumptions. They are only
copied to summer/winter after an explicit checkbox. A user can instead enter an
estimate or leave them unknown. Affordability calls the same Decimal budget
endpoint used by apartment assessment; no client-side financial formula is
introduced. District cards and saved candidates retain their source/date;
editing a candidate's rent changes it into a user-entered amount.

## API boundary artifact

`GET /api/v1/planner/district-boundaries` returns an attributed GeoJSON
FeatureCollection, cacheable for one day; missing artifact returns 503. No DB
is required. The list remains usable when geometry, WebGL or basemap tiles fail.
Basemap provider: OpenFreeMap Liberty, with OpenMapTiles and OpenStreetMap credit.
Personal budget figures are never sent to the map provider.
