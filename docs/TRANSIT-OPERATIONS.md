# Transit GTFS import — operations

All commands run from `backend/`. The import needs no API server and writes
only additive `transit_*` tables; housing tables and user databases are
never dropped or recreated (`create_all` only creates missing tables).

## Commands

```bash
python -m scripts.import_gtfs
python -m scripts.import_gtfs --validate-only
python -m scripts.import_gtfs --file /tmp/gtfs.zip
python -m scripts.import_gtfs --file /tmp/gtfs.zip --validate-only
python -m scripts.import_gtfs --file /tmp/gtfs.zip \
  --last-modified "Fri, 18 Sep 2026 12:29:14 GMT" --etag '"abc123"'
```

Exit codes: `0` success (including `already_current` and `superseded`),
`1` invalid feed or unusable local file, `2` download/HTTP failure,
`3` database lock conflict, `4` transaction error. Output is a concise
`validated:`/`activated:` line with entity counts plus warnings; never
credentials or full records.

## Tables (all additive, all writes go through the import CLI)

- `transit_feeds` — one row per validated generation: content SHA-256,
  source URL, `fetched_at`/`checked_at` (UTC), nullable source
  Last-Modified/ETag, agency timezone, effective calendar envelope,
  row counts, attribution/license/transformation evidence.
- `transit_state` — singleton (`id = 1`) holding `active_feed_id`.
- `transit_stops` — `(feed_id, stop_id)` with code, name, WGS84
  coordinates and nullable `parent_station`/`location_type`.
- `transit_routes` — `(feed_id, route_id)` with short/long names, the raw
  `route_type` and a derived mode (`tram`, `bus`, `trolleybus`, `other`).
- `transit_stop_services` — deduplicated
  `(feed_id, stop_id, route_id, service_id)` relationships.
- `transit_calendars` / `transit_calendar_exceptions` — weekday bands with
  date ranges and added/removed service dates.

## Transactions and retention

Validation (archive safety, CSV schema, reference and calendar checks)
runs before any write. Staging of one generation plus the `active_feed_id`
flip commits exactly once; any failure rolls everything back and the
previous pointer stays live. Compare-and-swap: a staged generation older
than a meanwhile-activated one is rolled back as `superseded` instead of
flipping. An identical content SHA records a new successful `checked_at`
without new rows. Old generations are retained and stay queryable; M08
does not delete or prune (avoids races with readers).

## Refresh failure recovery

A failed refresh changes nothing: timestamps, pointers and data keep
serving the last good generation. Recovery is always "fix the cause, run
the import again": unreachable source (exit 2), invalid feed (exit 1),
lock contention (exit 3) and transaction errors (exit 4) are distinct and
logged concisely. Suggested operator schedule is a daily import; no
automation is installed and the provider publishes no cadence, so this is
an operator choice, not a feed promise.

## Timestamps

- `fetched_at`: when this operator downloaded the bytes (UTC).
- `checked_at`: when this generation last passed full validation (UTC).
- `source_last_modified` / `source_etag`: provider metadata as observed;
  unknown for manually supplied files unless `--last-modified`/`--etag`
  are given. Re-downloaded identical content never resets the
  Last-Modified age. Never treat HTTP 200 as a modification date.
- Freshness policy for consumers (UTC now + Europe/Tallinn service date,
  injected in tests): `stale` when the successful check is older than 7
  days, source modification older than 30 days, or today outside the
  effective calendar envelope; `unknown` when not stale but the source
  modification is missing or more than 24 hours in the future; `current`
  otherwise. `current` means these checks pass, not real-time data.

## License evidence and credit

See `docs/TRANSIT-DATA-LICENSE.md`: CC BY-SA 3.0 derived transit data,
Tallinn credit, registry URL, license URL and transformation record,
stored per generation and served with future transit responses. Project
code stays MIT; salary/scenario data never enters these tables.
