# Relocation planner — M01 product specification

Status: review-ready proposal, 2026-09-21. Owner-directed planning by Codex.
This document defines future work; it does not change the running application
or supersede CONTEXT.md. Additive contracts are in PLANNER-CONTRACTS.md.
Provider-dependent decisions remain gated on DeepSeek's M02 evidence.

## Product promise

Enter your employment salary, protect your everyday spending and savings,
then understand which Tallinn housing options fit your budget. Assess an
apartment you found elsewhere, compare alternatives, and see the cash needed
to move in. Every estimate should explain its inputs and missing information.

Primary audience: a single adult planning to rent in Tallinn, with an
Estonian employment contract covered by the existing tax engine assumptions.
Initial planning models the user's full rent obligation, not household splits.
Room count means total rooms, not bedrooms. Currency is EUR throughout.

## Scope and navigation

| Route | Purpose | Delivery |
|---|---|---|
| `/{locale}/` | Explain the outcome; primary CTA opens planner | M04 |
| `/{locale}/planner` | Income, living budget, housing allowance | M06 |
| `/{locale}/explore` | District list/map, address assessment | M09–M11 |
| `/{locale}/compare` | Two or three manually added apartments | M12 |
| Existing calculator, housing, eresidency | Keep existing tools and URLs | All |

Header: Plan your move, Explore Tallinn, Tools, locale, theme. Tools exposes
the existing pages. Until a destination ships, do not publish its navigation
link. Existing calculator query keys `gross`, `pillar`, `basis` stay unchanged.
New scenario persistence has its own versioned namespace.

Do not promise available apartments: there is no confirmed listings feed.
District statistics are context, not offers. A user pastes or types an address
and enters an advertised rent; the app does not scrape a listing URL.

## Main journey

1. **Income.** Enter monthly gross employment salary and explicitly confirm
   the pension contribution. Show estimated net, tax year and assumptions.
   Use the existing `tooleping` calculation with `equalize_by=gross`; never
   select the regime with the largest net. Advanced regime comparison remains
   a separate existing tool. If those assumptions do not fit, offer manual net.
2. **Budget.** Enter monthly non-housing spending and a savings target.
   Choose a maximum housing share. Show both the share-based limit and the
   actual money left after these commitments; the smaller is the allowance.
   These are user choices, not official Estonian cost-of-living recommendations.
3. **Explore.** Choose total rooms. Show district estimates and their dates,
   with summer/winter utilities assumptions. List remains usable without a map.
   The user can also skip district browsing and assess a specific address.
4. **Assess.** Select a resolved address, enter rent and utilities if known.
   Show monthly range, remaining money after savings, move-in cash and nearby
   stops/routes. Unresolved address still supports budgeting; geographic facts
   stay unavailable. Nearby does not imply a short commute.
5. **Compare.** Pin two or three candidates. Compare the same expense and
   savings assumptions, summer/winter totals, one-time cash and data quality.
   Show trade-offs, without a fabricated quality score or automatic winner.
6. **Save/share.** Explicitly save on this device or export/share a chosen
   snapshot. No account required. Explain what personal data is included.

## Budget rules (M05 implementation boundary)

Use Decimal and ROUND_HALF_UP at two decimal places. Inputs are EUR/month
except move-in amounts, housing_share and pension rate. Let:

- N = monthly net income (existing tax service, or explicit manual input).
- E = monthly non-housing spending; excludes rent, utilities and savings.
- S = monthly savings target.
- p = chosen maximum fraction of net allocated to rent + utilities.
- A = N - E - S, signed money available after commitments.
- P = round(N * p, 2), share-based housing limit.
- H = max(0, min(A, P)), housing allowance.
- R = entered rent. U_s and U_w = summer/winter monthly utilities estimates.
- T_s = R + U_s; T_w = R + U_w, calculated only when that utility is known.
- L_s = N - E - S - T_s; L_w = N - E - S - T_w (signed remainder).

Fit is a comparison with the user's allowance, not financial advice:
`within_budget` if both seasonal totals <= H; `seasonal_risk` if only the
lower is <= H; `over_budget` if both exceed H; `unknown` if either is missing.
Use min/max of seasonal totals: do not assume winter is always more expensive.
At equality, the scenario fits. A negative A remains visible even though H=0.
Do not hide deficits or quietly reduce the savings target.

Recommended input UX: gross salary empty on first visit, pension requires a
choice; housing share prefilled 30% and labelled editable planning assumption.
E and S require explicit values, including zero. No fictional default food,
transport or childcare prices. Manual net permits zero; gross must be >0.
Cap money fields at EUR 1,000,000 and share at 0–100% as application limits.

### Utilities and incomplete knowledge

Utilities include building charges, heating, water and electricity as entered
by the user. Internet belongs in non-housing expenses unless explicitly
included in the entered utilities. Clarify this alongside the field.

Offer three modes: user seasonal amounts; an editable planning estimate; unknown.
Never infer a bill from an address alone. The existing `avg_utilities` is a
legacy estimate without seasonal provenance: do not relabel it as an observed
summer or winter bill. It may be offered as a clearly labelled single-value
starting assumption only after explicit user adoption, copied to both seasons.
Missing amounts remain null. For unknown utilities, show the rent-only subtotal
and `unknown` fit, and invite the user to ask for recent bills.

### Move-in cash

Fields: first rent payment, refundable deposit, broker fee, moving/setup cost.
Each is a direct entered EUR amount, not an invented mandatory multiplier.
`cash_needed = sum(all four)` only when all are known. Otherwise return the
known subtotal and list missing components. Explicit zero is valid; blank
does not mean zero. First rent may be prefilled from R with a visible label.
The deposit is cash tied up, not a recurring expense. Do not add the first
rent twice or include all future monthly bills in move-in cash.

## Data trust and integration boundaries

- Existing housing data: published aggregate snapshots plus legacy fallback.
  Expose row-level source and observation date before presenting it as sourced.
  A city-wide latest date must not conceal an older district row.
- Address search: backend adapter, normalized candidates; stable ID and
  coordinates only after M02 establishes provider semantics and coordinate CRS.
- District polygons and map tiles: licenses, attribution, quotas and operational
  suitability must be verified in M02. A public endpoint is not proof of permission.
- GTFS: import snapshots off the request path, validate then atomically activate.
  Nearby stops and listed routes only; no live arrivals or travel-time claims.
  Stop distance is straight-line metres, explicitly not walking distance.
- Apartment rents and bills: user-entered, not verified market data.
- Provider timeout: preserve the budget and comparison; show the affected
  feature unavailable. Never fabricate fallback places, bills or transit service.

Districts sort by selected room total (ascending), missing totals last, name as
tie-breaker. Include every district, even when none fit. For missing seasonal
utilities show unknown fit. A requested room category missing from the source
is unknown, never silently substituted with a smaller dwelling.

## Acceptance examples (synthetic arithmetic fixtures)

| N | E | S | p | R | U summer/winter | H | Remainder summer/winter | Fit |
|---:|---:|---:|---:|---:|---|---:|---|---|
| 2400 | 700 | 300 | .35 | 650 | 100 / 200 | 840 | 650 / 550 | seasonal_risk |
| 2400 | 700 | 300 | .35 | 600 | 100 / 200 | 840 | 700 / 600 | within_budget |
| 1200 | 1000 | 300 | .35 | 600 | 100 / 200 | 0 | -800 / -900 | over_budget |
| 2400 | 700 | 300 | .35 | 650 | null / null | 840 | null / null | unknown |

Move-in example: 650 first rent + 650 deposit + 0 broker + 200 setup = 1500.
If deposit is unknown, cash_needed=null and known subtotal=850.
These are test fixtures, not Estonia market estimates.

## Release and success criteria

First useful release is M04–M06: income to an explainable budget without any
external geography dependency. M07–M11 add place context; M12–M13 add comparison
and persistence. Publish no empty destinations ahead of their implementation.

Verify with users that they can identify the housing allowance, change winter
utilities, explain why a candidate exceeds budget, and distinguish a listing
price from a district estimate. Measure completion locally in usability checks;
production analytics is outside this release. No salary/address telemetry.

All new product UI ships in EN/ET/RU, light/dark, keyboard and mobile. Preserve
existing SEO, a11y and calculator URL behaviour. Test numerical edge cases,
unknown values, stale responses, provider failures, and locale changes.

Deferred: auto-import listings, household/multiple incomes, eligibility or
tax-residency engine, cars, EHR building data, live transit, commute routing,
accounts, server-side saved salaries, and AI-generated financial recommendations.
