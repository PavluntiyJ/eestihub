# Planner contracts — M01 proposed additive API

Status: review-ready design, not an active API contract. CONTEXT.md remains
authoritative until its owner incorporates accepted additions. Existing
endpoints, response types and calculator query keys remain unchanged.

## Stable core for M05–M06

Proposed endpoint: `POST /api/v1/planner/budget` (no persistence).
Thin route delegates to a budget service. Employment input reuses the existing
tax service directly; do not make an internal HTTP call or duplicate tax math.
All business arithmetic lives in the backend. Frontend consumes the response.

Request (employment variant):

```json
{
  "income": {
    "kind": "employment",
    "gross_monthly_income": 3000,
    "pension_pillar_rate": 0.02
  },
  "monthly_non_housing": 700,
  "monthly_savings": 300,
  "housing_share": 0.35,
  "apartment": {
    "rent": 650,
    "utilities": {"summer": 100, "winter": 200, "basis": "user_estimate"},
    "move_in": {"first_rent": 650, "deposit": 650, "broker_fee": 0, "setup": 200}
  }
}
```

`income` is a discriminated union. The second variant is
`{"kind":"manual_net","net_monthly_income":2400}`. Reject mixed variants,
extra fields and non-finite values. All fields above required except `apartment`,
which defaults to null. For an apartment, `rent`, `utilities`, `move_in` are
required; `move_in` may be null. Individual utility and move-in amounts may be
null to represent unknown. Money inputs >=0, <=1,000,000, at most two decimal
places; employment gross >0. Housing share from 0 to 1 inclusive with at most
four decimal places. Pension enum matches the existing tax request.
Parse Decimal from decimal text, not binary floating-point arithmetic.

Utility `basis` enum: `user_bill`, `user_estimate`, `legacy_assumption`, `unknown`.
`unknown` requires both amounts null; other bases require at least one amount.
`user_bill` describes what the user supplied, not independently verified bills.

Response example uses manual net=2400 and otherwise the same request:

```json
{
  "schema_version": 1,
  "income": {"kind": "manual_net", "net_monthly_income": 2400, "tax_year": null},
  "budget": {
    "monthly_non_housing": 700,
    "monthly_savings": 300,
    "housing_share": 0.35,
    "available_after_commitments": 1400,
    "share_limit": 840,
    "housing_allowance": 840
  },
  "apartment": {
    "rent": 650,
    "utilities": {"summer": 100, "winter": 200, "basis": "user_estimate"},
    "summer_total": 750,
    "winter_total": 850,
    "summer_remainder": 650,
    "winter_remainder": 550,
    "fit": "seasonal_risk",
    "move_in": {
      "cash_needed": 1500,
      "known_subtotal": 1500,
      "missing_components": [],
      "refundable_deposit": 650
    }
  },
  "warnings": []
}
```

Income response: kind, net_monthly_income and nullable integer tax_year only;
employment returns the year supported by the current engine, manual returns null.
Do not pretend to support arbitrary requested tax years. Any future year switch
requires its own contract change. `apartment` response null if not requested;
`move_in` response null if not requested. `refundable_deposit` nullable.
Money is serialized as JSON numbers, two-decimal computation precision; display
with Intl.NumberFormat. Match Pydantic schemas in TypeScript without `any`.

Warnings are objects `{code}` in deterministic code order. Initial codes:
`commitments_exceed_income` when available_after_commitments <0;
`utilities_incomplete` when an apartment has either utility unknown;
`move_in_incomplete` when supplied move-in has unknown components.
`missing_components` uses first_rent, deposit, broker_fee, setup in that order.
Frontend translates keys. Formulae and fit boundary rules are in PLANNER-PRODUCT.md.

HTTP: 200 valid calculation (including negative remainder), 422 invalid request.
Validation errors use FastAPI's existing envelope; frontend maps field locations
and provides localized fallback text. A budget call needs no database/provider.
Response header `Cache-Control: no-store`; do not log request bodies/income.
Request abort and sequence IDs on frontend prevent older responses replacing new
inputs. Stale output stays visibly stale until the current request succeeds.

## Geographic contracts — provisional until M02 review

These define UI needs, not a promise that any provider supports a field. M02
must supply example payloads, identity/CRS semantics, licensing and limits before
these schemas become implementation briefs. Do not invent raw provider fields.

| Proposed endpoint | Normalized result | Missing/failure behaviour |
|---|---|---|
| `GET /api/v1/addresses/search?q=...` | candidates: id, label, longitude, latitude, nullable district_id; attribution | 200 empty list for no match; 503 provider unavailable |
| `GET /api/v1/transit/nearby?lat=...&lon=...` | stops: id, name, straight_line_distance_m, coordinates, route names/types; feed metadata | 200 empty list is different from no feed (503) |
| `GET /api/v1/planner/districts?rooms=1` | stable district IDs, names, nullable rent, centroid; per-row provenance | missing rent stays null; DB outage 503 |
| `GET /api/v1/planner/district-boundaries` | attributed GeoJSON FeatureCollection with same district IDs | no verified polygons: omit map layer, preserve list |

Proposed bounds: query 3–200 trimmed characters, <=8 candidates; coordinates
finite lon -180..180, lat -90..90 and service-area filtering. Nearby radius
fixed at 800m, <=20 stops, sorted distance then ID; expose radius in response.
Routes are those associated with the active imported feed, not promised
departures. Feed validity, service calendars and stop/platform grouping policy
must be settled from M02; do not collapse distinct platforms solely by name.

Source metadata: provider key, source_url, observed_on (nullable), fetched_at
(UTC), attribution, freshness enum (`current`, `stale`, `unknown`). Current/stale
requires a documented per-source policy; do not infer freshness from HTTP 200.
District price provenance also records `published_aggregate` or `legacy_estimate`.
Legacy utilities must remain separately attributed and non-seasonal.

Search debounced 300ms, abort on new input, ignore stale responses. Use backend
timeouts and bounded caching appropriate to provider terms from M02. No API
keys in public env. Imported GTFS must keep last good snapshot on failed refresh;
serve stale data with its date or unavailable if none. Zip size/entry limits,
schema/foreign-key checks and atomic activation belong in M08's brief.

## Scenario state and sharing — M13 target

No automatic salary persistence. Hold working inputs in client state; explicit
"Save on this device" stores versioned input-only JSON. No backend account or
scenario DB. Include saved_at, currency=EUR, income, budget choices, up to three
candidates with optional address and the user-entered amounts. Recalculate on
load; saved results are not authoritative. Report unsupported versions/corrupt
data without crashing or overwriting the original. Handle unavailable storage.

Sharing is a separate explicit action: preview included fields, then generate
a versioned URL-fragment payload (not a salary in query params). Default includes
manual net/budget amounts and candidate costs; address and gross salary are
opt-in. Convert employment income to calculated manual net when gross omitted.
Without address, use Apartment A/B/C rather than leaking address through labels.
Fragments are readable by recipients and page scripts: never call them encrypted.
No automatic third-party telemetry. Strip external listing URLs and arbitrary HTML.

Use URL-safe encoded JSON with strict schema validation and a 6000-character
URL limit; offer JSON export if too long. Limit decoded payload to 16KiB and
three candidates. Show a review screen before importing; never auto-save a link
opened by a recipient. Unknown keys ignored only by an explicit version parser;
invalid/malformed payloads receive a localized error. Locale switch preserves
working state and fragment. Personal scenario pages use noindex and canonical
base routes; preserve current calculator link behaviour independently.
