# Planner release — September 2026

The owner approved a shorter release path: finish M08, ship apartment cost
assessment and an address map with nearby public transport, verify and release
on the existing Vercel + Render + Neon infrastructure. This decision supersedes
the earlier sequential M09–M13 delivery gates for this release only.

## Included

- Employment gross or manual net → explicit spending/savings → housing allowance.
- Apartment rent, nullable summer/winter utilities with user-declared provenance,
  and nullable move-in costs. All money calculations use the existing Decimal
  budget service. Blank means unknown; explicit zero means no cost. First rent
  is included in move-in cash and the refundable deposit is not monthly spending.
- Optional In-AKS Tallinn address selection, independent of apartment costs.
- Opt-in MapLibre map using OpenFreeMap Liberty. Salary/budget never enter map
  requests. The map has a list fallback, keyboard controls and attribution.
- Nearby individual GTFS platforms and routes scheduled for today's Tallinn
  date. No grouping by stop name, walking-time estimate, live arrival claim,
  rental listing feed or district recommendation.
- EN/ET/RU, stale-result handling, abort/retry, mobile layout and axe checks.

District polygons, area scoring, multi-apartment comparison, persistence and
shareable planner scenarios are deferred. The existing tax calculator's shared
URLs are unchanged. `district_id` on address candidates remains null.

## Additive API: GET /api/v1/transit/nearby

Required query parameters: `lat` (59.2–59.7), `lon` (24.3–25.1), finite WGS84
numbers. These bounds scope the query to the Tallinn area; they are not official
municipal polygons. Radius is fixed at 800 metres, limit at 20 platforms.

Response fields:

- `radius_m`, `limit`, `service_date`, `timezone: Europe/Tallinn`.
- `stops[]`: `id`, `name`, `longitude`, `latitude`,
  `straight_line_distance_m`, `routes[]` (`id`, nullable `short_name` and
  `long_name`, `mode: bus|tram|trolleybus|other`).
- `feed`: source URL, attribution, license URL/name, transformations,
  `fetched_at`, `checked_at`, nullable `source_last_modified`, calendar bounds,
  `freshness: current|stale|unknown`.

Only GTFS location type 0 (or omitted type) represents a platform. Exact
great-circle distance decides inclusion before rounding for display. Sort by
distance then opaque stop ID. Stops without routes today remain visible.
Calendars and add/remove exceptions are applied before route deduplication.
One captured generation supplies every read; at most seven database reads
serve all 20 platforms. No provider is called on the request path.

200 may contain an empty list. Missing feed/tables or unavailable database →
503 `detail.code: transit_unavailable`. Invalid coordinates → 422. Successful
and unavailable responses use `Cache-Control: no-store`.

## Release verification and operations

- Run backend pytest; PostgreSQL race tests must run in CI against the disposable
  `estihub_test` service, not production. SQLite alone cannot close M08.
- Run frontend build, lint, TypeScript, all Playwright flows and mobile axe.
- Live GTFS import goes through `python -m scripts.import_gtfs` against the
  intended database only. No automatic download on API startup or user requests.
- Follow [transit operations](TRANSIT-OPERATIONS.md) for refresh and provenance.
  Missing data visibly degrades to an unavailable message; never a fake stop list.
- Inspect the production budget, address lookup, nearby response, map and all
  three locales after deployment. Backend must deploy before the frontend smoke.
- No paid plan is authorized. Render's existing free-tier wake-up remains a
  hosting limitation; clients time out with retry while the service wakes.

## Dependency decisions

Next.js stays on the 15.5 maintenance line (15.5.25), with matching ESLint config.
MapLibre 6.10 is used because the 5.x line is covered by GHSA-jrc7-96c5-q579;
the worker is bundled locally and WebGL2 failure preserves the stop list.
PostCSS is overridden to patched 8.5.28 within its existing major version.
Lighthouse's development-only dependency advisories remain tracked separately;
do not downgrade LHCI or move Next.js to a new major through `audit fix --force`.

References: [MapLibre migration guide](https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/),
[MapLibre advisory](https://github.com/advisories/GHSA-jrc7-96c5-q579).
