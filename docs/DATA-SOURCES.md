# Data sources for future integrations

Research for the M02 task: address search, Tallinn public transport GTFS,
Tallinn district boundaries and a MapLibre basemap. **No product code was
changed in this pass** — the endpoints below are for a future map/search
feature.

- **Research date:** 2026-09-21
- **Worker:** opencode (deepseek-flash)
- **Method:** every URL was requested on the date above, from this checkout
  (`backend/scripts/probes/`) plus direct HTTP; the In-AKS UI was driven in a
  headless browser once to observe its real network traffic. No credentials
  or API keys were used or stored.

Labels used throughout:

- **[request]** — behaviour confirmed by an actual request in this pass.
- **[docs]** — read in provider documentation, not re-verified by a request.
- **[open]** — not resolved in this pass; needs a decision or follow-up.

## 1. Address search and geocoding — In-AKS (Maa- ja Ruumiamet)

In-ADS/In-AKS is the Estonian address data system. Two public hosts answer;
the new In-AKS UI uses the `aks.geoportaal.ee` one.

### Confirmed endpoints

Address search **[request]**:

```
GET https://aks.geoportaal.ee/inaks/inaadress/gazetteer
      ?results=3&appartment=1&unik=0&ky=1&iTappAsendus=1&address=Tartu+mnt+1
HTTP 200, application/json
```

Abbreviated first match:

```json
{
  "aadresstekst": "Tartu mnt 1",
  "pikkaadress": "Harju maakond, Tallinn, Kesklinna linnaosa, Tartu mnt 1",
  "ads_oid": "EE04064863",
  "adr_id": "2249878",
  "adob_id": "10725273",
  "tunnus": "121392807",
  "koodaadress": "377840298000005ZI00001EF000000000",
  "asum": "Kompassi asum",
  "sihtnumber": "10145",
  "viitepunkt_x": "543051.29",
  "viitepunkt_y": "6588822.17",
  "viitepunkt_l": "24.758626",
  "viitepunkt_b": "59.435048"
}
```

Reverse geocoding **[request]** — same endpoint, `x`/`y` in L-EST97
(EPSG:3301) instead of `address`:

```
GET https://aks.geoportaal.ee/inaks/inaadress/gazetteer
      ?results=3&appartment=1&unik=0&ky=1&iTappAsendus=1&x=543051.29&y=6588822.17
HTTP 200, first hit: "Tartu mnt 1"
```

The older host `https://inaadress.maaamet.ee/inaadress/gazetteer?address=...`
still answers with the same shape **[request]** (verified 200 with the same
first match). Prefer the `aks.geoportaal.ee` host, because the current In-AKS
UI calls it.

Stable identifiers and coordinates:

- `ads_oid` — the address object identifier in the address data system
  (`EE04064863`), the most stable key for cross-referencing an object.
- `adr_id`, `adob_id`, `tunnus` (building code), `koodaadress` (full address
  code) are additional identifiers carried by the response.
- `viitepunkt_x`/`viitepunkt_y` are L-EST97 (EPSG:3301);
  `viitepunkt_l`/`viitepunkt_b` are WGS84 longitude/latitude. The response
  also carries a WGS84 `g_boundingbox` and an L-EST97 `boundingbox`.

Observed but not documented **[request]**: the In-AKS UI also posts to
`https://aks.geoportaal.ee/aks-api/ava/api/ads/search` (search returns the
address polygon and `ads_oid`) and reads
`https://aks.geoportaal.ee/aks-api/ava/api/ads-address-component/list?level=1`
(administrative components). These were captured from UI traffic only; no
public contract for them was found in this pass **[open]**.

### Terms and limits

- Current provider terms, v1.2, 24 April 2026
  (`https://geoportaal.maaruum.ee/docs/aadress/In-AKS_kasutustingimused.pdf`,
  reviewed for M07): definition 1 and section 2.1.3 explicitly cover direct
  gazetteer requests; 2.2 permits free use and 2.3 permits automation.
  Section 3 concerns open data; section 4 separately retains rights in the
  service/software/materials. Use returned address data in our own UI; do not
  copy provider software/UI.
- Limits are per outbound IP: 5000 requests/10 minutes inside Estonia,
  2500/10 minutes outside Estonia — our Frankfurt backend uses the latter.
  Higher usage needs a provider agreement. Obsolete In-ADS limits do not apply.
- The official migration notice
  (`https://geoportaal.maaamet.ee/index.php?lang_id=1&page_id=1038`) keeps the
  legacy host temporarily redirected until end-2026: it is not an independent
  failover service, so the adapter must not fall back to it automatically.
- Current developer manual, v3.3.0, 23 April 2026
  (`https://aks.geoportaal.ee/inaks/inaadress/js/pdf/et/in_aadress_developer_manual.pdf`),
  sections 7.1/7.2: search, coordinates, quality and error envelopes.
- The earlier question whether any terms cover the gazetteer is resolved by
  these sources for ordinary use within the limits above; no agency contact
  was needed. The `.../kaarditeenuste-kasutustingimused-p24.html` map-service
  terms and the ADS X-tee integration pages remain background reading, not
  the basis for this integration.
- **M07 implementation (2026-09-22):** the backend adapter calls only the
  fixed gazetteer URL with a descriptive `User-Agent`, a five-second bound
  and <=1 MiB body; application-level budget (<=1000 calls/10 min, <=4 in
  flight, documented as single-process assumptions) stays inside the
  provider's per-IP limits. No `/aks-api/ava/...` routes, no reverse
  endpoint, no retry, no legacy fallback.

## 2. Tallinn public transport — GTFS

### Confirmed feed **[request]**

```
GET https://transport.tallinn.ee/data/gtfs.zip
HTTP 200, application/zip, 2,629,482 bytes
Last-Modified: Fri, 18 Sep 2026 11:10:54 GMT   ETag: "281f6a-65bbff4310b80"
Server: cloudflare
```

Archive contents (uncompressed row counts, 2026-09-21):

| File | Rows | Notes |
|---|---:|---|
| `agency.txt` | 1 | `tallinn`, Tallinn, `Europe/Tallinn`, lang `ee` |
| `routes.txt` | 80 | bus/trolley/tram routes, Estonian long names |
| `stops.txt` | 1120 | stop code, name, lat/lon |
| `trips.txt` | 20081 | |
| `stop_times.txt` | 483972 | ~17 MB uncompressed |
| `shapes.txt` | 36898 | |
| `calendar.txt` | 210 | service bands 2025-09-01 … 2027-09-01 |
| `calendar_dates.txt` | 2310 | holiday exceptions |

There is no `feed_info.txt`, so the feed itself carries no version or
publisher metadata.

The official open-data registry entry for the dataset
(`https://avaandmed.eesti.ee/api/datasets/5ccad39d-98a0-4ac4-ba0a-233ad5a83604`,
"Tallinna ühistranspordi peatused ja marsruudid") lists this distribution
**[request]**:

```json
{
  "titleEt": "Ühistranspordi peatused ja marsruudid",
  "license": "CC_BY_SA_3.0",
  "accessUrls": ["http://transport.tallinn.ee/data/gtfs.zip"],
  "applicableLegislation": ["ODD_LEGAL_ACT"],
  "updatedAt": "2026-05-22T08:48:27.840Z"
}
```

So the feed is **CC BY-SA 3.0**: attribution ("Tallinn") is required, and
derived data (for example tiles or a stops database published from it) must
be shared under the same license. The same registry entry cites
`https://transport.tallinn.ee/data/stops.xml`, which now returns 404
**[request]** — the GTFS zip is the working distribution.

Update cadence is **[open]**: the zip was modified 3 days before this probe
and carries Cloudflare caching; no published schedule was found.

**Recommendation:** ingest the GTFS zip, keep `stop_id`/`route_id` as keys,
attribute Tallinn and keep the share-alike obligation in mind for anything
redistributed. A GTFS parser library is worth adding at implementation time
(`stop_times.txt` is the large file).

## 3. Tallinn district boundaries

### City GIS service (GeoJSON, no token) **[request]**

```
https://gis.tallinn.ee/arcgis/rest/services/Linnaosad_asumid/MapServer
  layer 1 "Linnaosad" — 8 features, esriGeometryPolygon
  layer 0 "Asumid"    — 84 features, esriGeometryPolygon
```

GeoJSON query that works without authentication:

```
GET .../Linnaosad_asumid/MapServer/1/query
      ?where=1%3D1&outFields=*&f=geojson&resultRecordCount=1
HTTP 200, FeatureCollection, geometry MultiPolygon
```

First feature properties include `nimi` ("Haabersti linnaosa"), `animi`,
`pindala` (area), `muutmis_kp`, EHAK/administrative codes. A `FeatureServer`
also exists. The service and layer metadata have an empty `copyrightText`
**[request]**, so the license is not stated by the service itself.

### Official dataset and license (downloadable files) **[request]**

The registry entry
`https://avaandmed.eesti.ee/api/datasets/e147cc7d-6063-40e3-b614-0ea1696f225a`
("Tallinna linnaosade ja asumite kaardifailid", Tallinn) lists all
distributions under **CC BY-SA 3.0**, with:

- "Asumipiirid (GIS failid seisuga 02.06.2020)" — SHP, GDB, DGN, DWG (2020)
- "Tallinna asumite skeem 2019" — PDF
- landing page `https://www.tallinn.ee/et/geoportaal/ruumiandmed`
  ("Tallinna asumite piirid (uuendatakse vajadusel)")

That license covers the files distributed through the registry. The live
ArcGIS service is a different channel: it states no license (empty
`copyrightText` **[request]**), and mapping the registry license onto the live
layer is **not supported by this evidence** — treat that mapping as
unresolved **[open]** until the city confirms it. Attribution ("Tallinn") and
share-alike apply to the downloadable files; the live service is updated as
needed while the static files are dated 2020.

Alternatives **[docs]**, not probed:

- Maa- ja Ruumiamet "Haldus- ja asustusjaotus"
  (`https://geoportaal.maaruum.ee/est/Ruumiandmed/Haldus-ja-asustusjaotus-p119.html`)
  is the authoritative national dataset; its map-service terms allow
  commercial use with attribution. No direct WFS endpoint was located in this
  pass **[open]**.
- OSM district polygons via Overpass would be available under ODbL
  (attribution + share-alike); not requested in this pass.

**Recommendation:** if the feature needs a license it can redistribute
without share-alike, neither of the confirmed sources is clean — resolve the
live-service license in writing or use the Maa-amet route first. If
share-alike is acceptable, the city's CC BY-SA 3.0 files are the documented
choice; taking current geometry from the unlicensed live REST service should
not be presented as licensed until the mapping is confirmed.

## 4. Basemap for MapLibre

| Provider | Probe URL | Result | Key | Terms summary |
|---|---|---|---|---|
| OpenStreetMap | `https://tile.openstreetmap.org/3/4/2.png` | **200** PNG, `CORS: *` | none | **[docs]** tile usage policy: valid UA/Referer, no bulk download or prefetch, cache per headers, attribution; best-effort, blocks possible |
| CARTO | `https://a.basemaps.cartocdn.com/light_all/3/4/2.png` | **200** PNG, `CORS: *` | none | **[docs]** attribution required for every plan; free-tier commercial terms **[open]** (docs page did not render server-side) |
| Stadia Maps | `https://tiles.stadiamaps.com/tiles/alidade_smooth/3/4/2.png` | **401** without key | required | **[docs]** Free $0: 200k credits/month, "commercial use not allowed"; Starter $20/mo allows commercial |
| MapTiler | `https://api.maptiler.com/maps/streets-v2/style.json` | **403** without key | required | **[docs]** Free $0 for testing/PoC/personal/non-commercial with logo; Flex $30/mo |
| OpenFreeMap | `https://tiles.openfreemap.org/styles/liberty` | **200** JSON style, `CORS: *` | none | **[docs]** public instance free including commercial use, no limits, no registration, no cookies, no SLA; OSM data; self-hostable |
| MapLibre demo | `https://demotiles.maplibre.org/style.json` | **200** JSON | none | **[docs]** demo tiles only, not for production |
| Maa-amet WMS | `https://kaart.maaamet.ee/wms/alus?service=WMS&version=1.1.1&request=GetCapabilities` | **200** XML, layers `MA-ALUS`, `pohi_vr2`, `pohi_vv`, `of10000`, … | none | **[docs]** free, commercial use allowed with attribution ("Aluskaart: Maa- ja Ruumiamet [aasta]"); no mass caching; SRS is **EPSG:3301 only** |

Two findings matter for MapLibre:

- MapLibre's raster source supports the WMS tile token
  `{bbox-epsg-3857}` **[docs]**, verified in the MapLibre style-spec sources
  documentation. A WMS must serve Web Mercator for that token to work.
- Every Maa-amet `wms/alus`, `wms/kaart`, `wms/hallkaart` and `wms/fotokaart`
  service advertises `EPSG:3301` only **[request]** (other CRS were not found
  in the capabilities), so it cannot be used directly as a MapLibre raster
  source without a reprojecting proxy or a separate tile build.

**Recommendation:** use **OpenFreeMap Liberty** as the MapLibre basemap
(default no-key vector style, no request limits, OSM attribution). Use the
Maa-amet WMS only behind a reprojection/tile cache if authoritative Estonian
detail is required. Keep the public OSM tile server for development and
low-traffic use only, with a descriptive `User-Agent`/`Referer` and
attribution; do not plan on Stadia or MapTiler without a paid commercial plan,
and confirm CARTO's free-tier terms before commercial use.

## Reproducing the probes

All probes are stdlib-only and print what they requested:

```bash
cd backend
python -m scripts.probes.probe_inaks
python -m scripts.probes.probe_inaks --address "Narva mnt 5"
python -m scripts.probes.probe_inaks --reverse 543051.29 6588822.17
python -m scripts.probes.probe_gtfs
python -m scripts.probes.probe_districts
python -m scripts.probes.probe_basemap
```

## Open questions for the next iteration

- Address gazetteer terms resolved for M07 (In-AKS v1.2 terms, per-IP
  limits above); re-check only if usage approaches the limits or leaves
  ordinary direct-request use.
- Publish/confirm the GTFS update cadence; the registry metadata
  (2026-05-22) lags the file's Last-Modified (2026-09-18).
- Decide how CC BY-SA 3.0 share-alike affects a derived district layer or a
  GTFS-based map before shipping one.
- Confirm whether the live Tallinn ArcGIS `Linnaosad_asumid` service may be
  used under the registry's CC BY-SA 3.0 file license; the service itself
  states no license. This mapping is unresolved **[open]**.
- CARTO free basemap terms for commercial use could not be confirmed from the
  documentation in this pass.
- The "Maa- ja Ruumiamet avatud ruumiandmete litsentsitingimused" link on the
  terms page resolves to 404 **[request]**; ask the provider for the current
  license URL if the download services are used.
