# M05–M06 handoff (owner-directed, 2026-09-22)

Implement M05 then M06, sequentially, with separate commits. Stop after M06
for review. This packet continues the owner's requested planner implementation.
Read CONTEXT.md in full and retain its stack, tax rules and existing APIs.
The requested additive budget API is specified in PLANNER-CONTRACTS.md under
"Stable core for M05–M06"; formulae are in PLANNER-PRODUCT.md. These specify
the new feature for this owner-directed packet; geographic/sharing contracts
remain proposals. Report the addition for CONTEXT's owner; protected files
and tasks/ remain untouched. Do not change existing contracts.

## M05 — backend budget calculation

Own new schemas/planner.py, services/budget_service.py, api/v1/routes/planner.py
inside backend/app, backend/tests/test_planner.py, required router registration,
and TODO.md. Read registration before modifying only the required lines.
Tax-year metadata may be added to core/tax_rates.py; existing rates stay intact.

- POST /api/v1/planner/budget: employment or manual net, spending, savings,
  housing share, optional apartment with seasonal utilities and move-in costs.
- Reuse existing employment calculation; do not choose the highest-net regime.
- Decimal/ROUND_HALF_UP, numeric JSON output, explicit null for unknown costs,
  signed deficits, strict validation, Cache-Control: no-store.
- No DB/provider dependency, persistence, salary logging or new packages.
- Tests: all four product fixtures, exact allowance boundary, zero income/share,
  rounding, reversed seasons, partial utilities/move-in, invalid inputs and
  employment parity. Assert JSON number types and HTTP 422 for invalid requests.
- Run the full backend suite, then commit:
  `feat(budget): add monthly and move-in calculations`.

## M06 — guided income and budget UI

Start after M05 checks pass. Own new localized planner page and features/planner;
planner additions to types/api.ts and lib/api.ts; planner translations in EN/ET/RU;
homepage primary CTA, navigation and matching keys; public planner sitemap entry;
planner e2e tests, README feature list and TODO.md. Limit shared edits to this feature.

- Follow PLANNER-DESIGN.md and existing M04 tokens. Gross starts empty, pension
  choice explicit, manual net alternative, explicit spending/savings including
  zero, editable housing share initially 30%.
- Backend is the calculation authority. Show net, supported tax year for
  employment, both budget limits, final allowance and explanatory warnings.
- Abort obsolete requests and ignore stale responses. Mark results stale after
  input changes; preserve inputs on errors and allow retry.
- Add a real planner navigation link and homepage CTA only when it works.
  Until M09, link to the existing housing overview as general context, not a
  personalized map. No dead Explore links.
- EN/ET/RU, both themes, mobile and keyboard. No automatic persistence or
  salary in URLs. Preserve existing calculator URLs. Keep draft in client state;
  reload may reset it. Warn before locale navigation discards an unsaved draft.
- No apartment/map/comparison screens or external integrations in this module.
- Test employment/manual net, validation, zero amounts, stale-response ordering,
  retry, keyboard operation, mobile and locale handling. Run build, lint,
  backend suite and seeded e2e/axe. Inspect actual desktop/mobile screenshots.
- Commit: `feat(planner): add guided income and budget flow`.

## Handoff and ownership

Do not stage the whole shared tree. Codex has uncommitted planning docs and a
small M04 dictionary-structure fix; preserve them and keep unrelated changes out
of implementation commits. Mark modules [R], record checks and commits in TODO,
report the new API for CONTEXT section 5, and stop before M07. Update README only
for delivered functionality; report stale counts/documentation outside ownership.
