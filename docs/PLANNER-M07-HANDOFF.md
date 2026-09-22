# M07 — verified Tallinn address search

Owner-directed handoff from Codex review, 2026-09-22. Implement M07 only,
then stop for review. This packet resolves the address-search part of M02;
it does not accept transit, polygon or tile integrations. Read CONTEXT.md,
PLANNER-PRODUCT.md and PLANNER-DESIGN.md. Preserve the stack and existing APIs.
This additive contract replaces the provisional address-search row in
PLANNER-CONTRACTS.md for this packet. Protected instructions and tasks remain
untouched; report incorporation into CONTEXT to its owner.

## Verified sources and gate decision

- Current provider terms, v1.2, 24 April 2026:
  https://geoportaal.maaruum.ee/docs/aadress/In-AKS_kasutustingimused.pdf
  Definition 1 and section 2.1.3 explicitly cover direct gazetteer requests;
  2.2 permits free use and 2.3 permits automation. Section 3 concerns open
  data; section 4 separately retains rights in the service/software/materials.
  Use returned address data in our own UI; do not copy provider software/UI.
- Limits are per outbound IP: 5000 requests/10 minutes inside Estonia,
  2500/10 minutes outside Estonia. Our Frankfurt backend uses the latter.
  Higher usage needs a provider agreement. Do not use obsolete In-ADS limits.
- Official migration notice:
  https://geoportaal.maaamet.ee/index.php?lang_id=1&page_id=1038
  The legacy host is temporarily redirected until end-2026, not an independent
  failover service. Do not add automatic fallback to it.
- Current developer manual, v3.3.0, 23 April 2026:
  https://aks.geoportaal.ee/inaks/inaadress/js/pdf/et/in_aadress_developer_manual.pdf
  Sections 7.1/7.2 define search, coordinates, quality and error envelopes.
- Codex independently reproduced HTTP 200 for Tartu mnt 1 (EE04064863),
  Tallinn Mustamae tee 5 (ME02092715), and a no-match host-only object.

The claim that gazetteer terms cannot be found is superseded by these direct
sources. Address-search implementation can proceed without contacting the
agency for ordinary use within its limits. Other M02 gates remain separate.
No public deployment or provider contact is assigned by this brief.

## Scope and ownership

Backend: new address schema/service/route and tests, minimal router registration,
configuration and .env.example additions. Reuse available packages or stdlib;
do not introduce a framework, DB table or migration.
Frontend: new features/addresses combobox, matching types/API helper,
EN/ET/RU strings and tests. Mount an optional address-search section below the
planner's successful result, clearly separate from the budget form. It selects
and displays a Tallinn address as location context only; it does not affect
budget arithmetic or claim apartment availability, district fit or transport.
Preserve the budget on search failures. No new empty navigation destination.
Docs: update address section/open questions in DATA-SOURCES.md, README only
for delivered behaviour, and TODO. Do not stage unrelated dictionary repairs
or Codex planning documents. Commit `feat(addresses): add Tallinn address search`.

## Frozen endpoint

GET /api/v1/addresses/search?q=...
Trim q; require 3–200 Unicode characters, reject controls and repeated q.
Invalid input: 422, no provider call. A valid successful response is:

```json
{
  "query": "Tartu mnt 1",
  "candidates": [{
    "id": "EE04064863",
    "label": "Harju maakond, Tallinn, Kesklinna linnaosa, Tartu mnt 1",
    "short_label": "Tartu mnt 1",
    "longitude": 24.758626,
    "latitude": 59.435048,
    "district_id": null,
    "quality": "exact"
  }],
  "attribution": {
    "provider": "maa_ja_ruumiamet",
    "label": "Maa- ja Ruumiamet / In-AKS",
    "source_url": "https://geoportaal.maaamet.ee/est/teenused/integreeritav-aadressiotsing-in-aks-p504.html"
  }
}
```

At most eight candidates; deduplicate opaque ads_oid preserving provider order.
Do not promise permanent identity from two observations. Match quality is
exact for tapne_lahiaadress/tapne_taisaadress, partial for osaline, unknown
otherwise (including missing values); never infer building eligibility.
Use pikkaadress/aadresstekst for labels; parse finite viitepunkt_l/b as lon/lat
within global coordinate bounds. No L-EST conversion or district inference.
Accept only Tallinn rows (omavalitsus == Tallinn); district_id remains null.
Missing required ID/labels/coordinates in an in-area row is provider failure,
not an empty successful search. Non-Tallinn rows can be filtered normally.

No match: 200 with candidates=[] and attribution. Recognize an empty addresses
array or an otherwise valid host-only no-match envelope; arbitrary JSON is
not automatically a no-match. An upstream error key, malformed schema/JSON,
HTTP failure or timeout returns 503 with detail.code=address_provider_unavailable.
Local outbound budget exhaustion: 503 with detail.code=address_search_busy
and Retry-After. Do not expose upstream error text or raw responses to users.
All responses use Cache-Control: no-store. No salary fields in this endpoint.

## Adapter and resource limits

Fixed upstream https://aks.geoportaal.ee/inaks/inaadress/gazetteer;
URL-encode address=q, results=8, appartment=1, unik=0, ky=1, iTappAsendus=1.
No user-supplied upstream URL, private /aks-api/ava routes, reverse endpoint,
automatic retry or legacy fallback. No claim of exhaustive Tallinn coverage:
filtering eight nationwide hits can produce fewer than eight city matches.
Use a descriptive User-Agent, five-second bounded request and <=1 MiB body.
Do not block an async event loop with synchronous networking.

Cache normalized successful results in memory for 60 seconds, <=256 entries;
do not cache failures or persist queries. Use a thread-safe outbound limiter,
conservatively <=1000 provider calls in any rolling ten minutes and <=4 in
flight per process; cache hits do not consume the provider budget. Document
that these bounds assume one process/instance per egress IP; multiple workers
or replicas require a shared quota before scaling. Never present these
application limits as provider-published limits. Do not log query contents in
application diagnostics; document that GET URLs may appear in access logs.

## UI and verification

500ms debounce, four characters for automatic search; explicit search accepts
three. These are conservative product defaults, not claimed requirements of
the current terms. Enter/arrow keys/Escape, labeled combobox/listbox/options,
aria-expanded/controls/activedescendant and loading/result announcements.
Only explicit selection creates a selected address. Editing or clearing text
clears the old selection immediately. Abort obsolete calls, ignore late
responses, clean up on unmount; preserve query on failure and offer retry.
Distinct empty, unavailable and busy messages. Attribution remains visible.
No persistence, telemetry, salary URL changes, external map or transit dependency.

Backend tests mock transport with sourced minimal fixtures: exact/partial/
unknown quality, host-only/empty results, out-of-area, duplicate IDs, string
coordinates, invalid coordinates/rows, error envelope at HTTP 200, non-200,
timeout, invalid/oversized body, validation boundaries, cache expiry/eviction,
limiter and no retry/fallback. CI must not depend on live provider availability.
Browser tests mock address API: debounce, keyboard selection, clear/edit,
late responses, retry, empty vs unavailable, preserved budget, all locales,
mobile and both themes. Existing budget tests remain real-backend tests.
Run full pytest, build, lint and seeded e2e/axe; inspect desktop/mobile UI.
Run one modest manual live search and no-match check outside CI; record date.

Documentation impact: replace DATA-SOURCES' unresolved gazetteer-terms claim
with current source and limits; leave other unresolved sources marked open.
Record exact checks, commit and remaining concerns in TODO with status [R].
Stop after M07; M08–M09 require their own briefs/reviews.
