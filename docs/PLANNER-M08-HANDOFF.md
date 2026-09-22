# M08 — versioned Tallinn GTFS import and refresh

Owner-directed implementation packet, Codex review, 2026-09-22.
Implement M08 only and stop for review. Read CONTEXT.md in full, the planner
product spec and this brief. No frontend, nearby API, map, production import,
scheduled automation, push or deployment in this packet. M10 will consume the
stored data; M09 has separate map/geometry gates. Preserve all existing APIs,
tables and unrelated working-tree edits. Do not edit protected files/tasks.

## Evidence and license handling

Source: https://transport.tallinn.ee/data/gtfs.zip
Registry evidence recorded in DATA-SOURCES.md:
https://avaandmed.eesti.ee/api/datasets/5ccad39d-98a0-4ac4-ba0a-233ad5a83604
Worker's 2026-09-22 probe reports 1120 stops, 80 routes, 20081 trips,
483972 stop times, calendar and exception files, no feed_info.txt.
These are observations, not permanently required counts or an uptime promise.
Codex's repeat requests to the registry/feed returned 403 on this pass;
do not claim independent live confirmation. Retain the worker's source
metadata evidence and recheck normal access before any production rollout.
Never evade access controls; 403 is a failed refresh preserving the old feed.

Use the recorded CC BY-SA 3.0 distribution license as the implementation basis.
Primary license: https://creativecommons.org/licenses/by-sa/3.0/legalcode.en
Implementation decision: keep imported/normalized transport data separately
identified; preserve Tallinn attribution, dataset title, original source and
license URL, and describe transformations. Mark distributed derived transit
data under CC BY-SA 3.0. This does not relicense independently written project
code or combine salary/scenario data into the licensed transit dataset.
Do not claim that all service software or all database contents have this
license. Capture exact licensor/credit metadata from the recorded distribution;
do not replace it with a guessed author. Add docs/TRANSIT-DATA-LICENSE.md.
This concrete handling resolves the development gate; public release still
requires the retained source-license evidence and attribution to be reviewed.

## Ownership and delivery

Own new backend/app/models/transit.py, services/transit_import.py and
services/transit_data.py, scripts/import_gtfs.py, tests/test_transit*.py,
docs/TRANSIT-OPERATIONS.md and docs/TRANSIT-DATA-LICENSE.md. Minimal model
registration/config/.env.example changes are allowed. Update the GTFS section
of DATA-SOURCES.md and README for delivered commands only, plus TODO.
Use SQLAlchemy and stdlib csv/zipfile; no new package, database engine,
migration framework, provider, service or frontend dependency.
Existing project create_all practice may create additive transit tables via
the import CLI; never drop or recreate housing tables or user databases.
Suggested commit: `feat(transit): import versioned Tallinn GTFS snapshots`.

CLI: `python -m scripts.import_gtfs` downloads the fixed source into bounded
temporary storage, validates, stages and activates. `--file PATH` supports
offline validation/import from a local archive; a manually supplied file has
unknown source timestamps unless supplied through validated metadata.
`--validate-only` performs all archive/data checks without database writes.
Exit nonzero for invalid feed, HTTP failure, lock conflict or transaction error;
print a concise reason and counts, without credentials or full records.
No automatic download during API startup, deployment startup or HTTP reads.

## Input safety and validation

- Limits chosen for this application: 50 MiB compressed, 200 MiB total
  uncompressed, 100 MiB per entry, 32 entries, 2 million CSV rows per file,
  64 KiB per cell. Bound actual streamed bytes as well as ZIP metadata;
  Content-Length alone is insufficient. Stream stop_times, not a huge row list.
- Reject duplicate member names, encryption, symlinks, nested archives,
  absolute/traversal paths and malformed ZIP/CRC/CSV/UTF-8. Never extractall.
  Read needed root-level .txt members directly; tolerate extra GTFS files
  within limits but do not parse shapes/vendor fields into product features.
- Fixed HTTPS source, no arbitrary remote URL option. Use a descriptive
  User-Agent, finite socket timeout and a separately enforced total download
  deadline (60 seconds); no retry loop. Slow-drip responses must stop as well
  as silent responses. Keep download/parse outside activation transactions.
- Parse agency timezone, stops, routes, trips, stop_times, calendar and
  calendar_dates. At least one calendar file is required. Ignore shapes.
  Require headers, unique entity IDs, valid dates/weekday flags/exception
  values, finite global coordinate bounds and valid route types. IDs remain
  opaque strings with leading zeros preserved.
- Validate trip->route/service and stop_time->trip/stop references, and
  uniqueness of (trip_id, stop_sequence). Reject incomplete relationships;
  resolve services through calendars or exception-only service definitions.
  Stop/route/trip/stop_time datasets must be nonempty; do not hardcode counts.
  Log suspicious count reductions relative to the active generation for review.
- Preserve every stop_id, including route-less stops; no grouping by name or
  stop_code. Empty location_type means GTFS's default stop/platform type.
  Retain nullable parent_station/location_type if future feeds supply them;
  validate parent references, but do not invent groups. Regional stops may
  exist: do not impose an invented Tallinn administrative bounding box.
- Preserve original route_type. Derived mode: 0/900 tram, 3/700 bus, 11/800
  trolleybus; other valid supported codes retain raw type and map to other.
  Source for extended codes:
  https://developers.google.com/transit/gtfs/reference/extended-route-types

## Generations and calendars

Use feed-generation-scoped keys for stops, routes and service associations.
Store feed metadata: content SHA-256, source_url, fetched_at, checked_at,
nullable parsed Last-Modified, optional ETag, agency timezone, calendar range,
row counts, attribution/license and transformation description.
Choose internal table names within the owned model file. A singleton state
row holds active_feed_id. Keep at least the previous good generation; no
automatic deletion/pruning in M08, avoiding races with readers.

Do NOT store only stop_routes pairs over all trips and discard service IDs.
Retain deduplicated (feed_id, stop_id, route_id, service_id) relationships,
weekday/date calendars and date exceptions. Trips/stop_times may be transient
join inputs; persisting half a million stop_times is unnecessary for this slice.
Provide an internal service helper returning routes for a stop on a supplied
service date in Europe/Tallinn, applying additions/removals before deduplication.
Routes here mean scheduled on that date, never live departures or guaranteed
service. Route-less or no-service-today stops return an empty route list.
No timetables, arrival calculation, commute estimation or nearby HTTP endpoint.

GTFS reference:
https://gtfs.org/documentation/schedule/reference/#calendar_datestxt
The maximum calendar end_date is only an envelope, not proof every service
is current until that date. Derive calendar_start/calendar_end from the union
of effective referenced service dates, including exceptions. Do not label it
as a publisher-guaranteed expiry date. Test weekday gaps and exception-only
services; do not infer coverage from min/max alone.

Validate fully before atomic activation. Insert all new generation rows and
flip active_feed_id in a transaction; failure leaves the previous pointer
and data intact. Reads capture one active generation ID for the whole result.
Prevent concurrent imports from overwriting a newer activation with older
staged content: lock/compare-and-swap active state, including first import.
Test with PostgreSQL for lock/transaction behavior; SQLite tests alone are
not evidence of PostgreSQL activation safety. Old data remains queryable.
Identical active SHA is idempotent: do not create duplicate rows/generations;
record successful check time only after a fully validated download.

## Freshness policy (our policy, not the publisher's cadence)

Use injected UTC now and Europe/Tallinn service date for deterministic tests.
Maintain separate operational check time and source modification time:

- stale: latest successful check older than 7 days, or known Last-Modified
  older than 30 days, or today's date outside the effective calendar envelope.
- unknown: not stale by known evidence, but Last-Modified is missing/invalid
  or implausibly future-dated (>24 hours ahead).
- current: otherwise. Current means meets these checks, not real-time data
  or that every route operates today; use the calendar helper for that.

Failed refresh never updates successful check/source timestamps. Re-downloading
unchanged old content does not reset Last-Modified age. Never create an
observation date from HTTP 200 or use fetched_at as source modification time.
An unavailable/no-active-feed state is distinct from an empty stop route list.
Keep stale good data available with metadata for the future API to label.
Document daily refresh as a suggested operator schedule; do not create an
automation or claim that the provider publishes daily. No frontend changes.

## Acceptance and documentation

Tests use tiny synthetic ZIPs and fake HTTP transport/time; CI needs no live
feed. Cover valid fixture, exact counts/joins, opaque IDs, duplicate IDs,
missing files/headers, malformed cells/dates/coordinates, orphan refs,
duplicate stop sequence, no parent grouping, route-less stop, route mapping,
weekday/weekend, add/remove exceptions and exception-only calendars, expired
and future service, freshness thresholds/unknown timestamps, idempotent SHA,
changed-feed activation, rollback after injected failure, concurrent writers,
and retained old-generation reads. Include archive/download limits and slow
response deadline; no real sleeping for freshness tests.

Run full backend tests, frontend build/lint as regression guards, and focused
PostgreSQL import/rollback/concurrency integration checks against an isolated
test database (never production). Clearly report an unavailable local Postgres
check rather than claiming SQLite proved it. A small manually downloaded feed
validation can be recorded if accessible; a 403 must not be bypassed or hidden.

Operations doc: exact import/validate commands, additive table creation,
transaction/retention behavior, refresh failure recovery, timestamp meanings,
license evidence/credit and the future daily-refresh option. README must not
claim a delivered transit UI/API yet. Update DATA-SOURCES' parser-library
recommendation and calendar assumptions; preserve unresolved map-license notes.
TODO: status [R], model/commit/checks and Notes for CONTEXT's owner describing
additive tables/internal services, with no edits to protected files. Stop M08.
