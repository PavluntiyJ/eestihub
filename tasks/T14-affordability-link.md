# T14 — Affordability link: net salary → affordable Tallinn districts

**Read first:** `docs/CONTEXT.md` (§2, §4–§6).
**Dependencies:** none (both APIs exist). **Role:** Frontend.
**Branch:** work in `main` (or a feature branch if the orchestrator says
so).

## Context

The MVP has two disconnected features: the tax calculator returns
`net_income` per regime, and the housing dashboard returns average rents
per district. This task connects them: after a calculation, the user
sees which Tallinn districts they can afford to rent in. Pure frontend
work — no backend changes, both endpoints are live
(`POST /api/v1/calculate-taxes`, `GET /api/v1/housing/rents`).

## Steps

1. **Data flow.** On `/[locale]/calculator`, fetch the housing rents
   server-side (same pattern as the housing page) and pass the
   serializable districts array as props to the client calculator form.
   If the backend is unreachable, hide the panel and keep the page at
   200 (established offline-tolerance rule).
2. **Affordability rule.** Budget = 30% of the best regime's
   `net_income` (rounded down to whole euros; the 0.30 factor lives in
   one named constant in the feature code). For each district pick the
   largest room category whose average rent fits the budget; districts
   with no fitting category are omitted. Render an "affordable
   districts" panel below the result cards: budget line + list of
   `district — room category` entries, reusing the existing room-category
   labels from the housing dictionaries if present.
3. **i18n.** New `affordability` namespace in
   `src/messages/{en,et,ru}.json`; keys symmetric across locales; no
   hardcoded user-facing strings.
4. **e2e.** Extend the calculator smoke: after the €3000/2% submit,
   assert the affordability panel renders with at least one district.

## Non-goals

- No backend changes; no new API fields.
- No map, chart, or trend UI (backlog).
- No URL-share/year-toggle on the calculator (backlog).
- No changes outside: `features/tax-calculator/`, `features/housing/`
  (only if reusing components/types), `messages/*.json` (add your
  namespace only), `types/api.ts` (reuse existing types, do not
  duplicate), `e2e/`.

## Acceptance criteria

- [ ] `npm run build` passes; no `any`.
- [ ] With both endpoints up: submit €3000/2% → panel shows the budget
      and ≥1 affordable district, localized in en/et/ru (spot-check via
      prod build + curl or browser).
- [ ] Backend fully down: calculator page stays 200, panel absent, no
      crash.
- [ ] `npm run e2e` passes including the extended smoke.
- [ ] `'use client'` count grows only inside
      `features/tax-calculator/`.

## Verification

- `cd frontend && npm run build && npm run e2e` (backend on :8000,
  compose db + seed as usual).
- Commit: `feat(calculator): affordability panel linking net salary to
  district rents`.

## On completion

Set T14 to `[R]` in `TODO.md` + a journal entry (what was verified and
how).
