# T14 — Affordability link: net salary → affordable Tallinn districts

**Read first:** `docs/CONTEXT.md` (§2, §4–§6).
**Dependencies:** T17 — it changes the net-income figures this panel is
built on and adds the comparison-basis toggle. Start only when T17 is
`[R]` or later. **Role:** Frontend.
**Branch:** work in `main`.
**Runs in parallel with:** T19. **Blocks:** T20.

> Rebased 2026-09-02. The original version of this brief budgeted against
> "the best regime's net income" with a hidden 0.30 constant. Both parts
> changed: after T17 there is no single "best" regime without saying on
> what basis, and the audit's view is that a factor the user cannot argue
> with is a factor they will not trust. Read the steps as written, not
> any earlier copy.

## Context

The MVP has two disconnected features: the tax calculator returns
`net_income` per regime, and the housing dashboard returns average rents
per district. This task connects them — after a calculation, the user
sees which Tallinn districts they could afford to rent in. Pure frontend
work; both endpoints are live.

## Steps

1. **Data flow.** On `/[locale]/calculator`, fetch the housing rents
   server-side (same pattern as the housing page) and pass the
   serializable districts array as props to the client calculator form.
   If the backend is unreachable, hide the panel and keep the page at
   200 — the established offline-tolerance rule.

2. **Budget basis.** The budget comes from the net income of the regime
   the user is looking at, under the comparison basis they selected in
   T17 — not from a hardcoded "best". If the results are ranked, use the
   top-ranked regime and **name it in the panel**, so the number is never
   unattributed. Recompute when either the basis or the input changes.

3. **Affordability rule.** Budget = share × net income, rounded down to
   whole euros. The share defaults to 30%, and is a **user control** — a
   slider or a small set of preset shares, labelled, with the resulting
   euro budget shown live. The default lives in one named constant in the
   feature code; the range and step live next to it. For each district,
   pick the largest room category whose average rent fits the budget;
   districts where nothing fits are omitted, and the panel says so rather
   than rendering an empty box.

4. **Rent plus utilities.** Compare against rent **and** average
   utilities, not rent alone — €170–210 a month is exactly what decides
   this question, and the field is already in the API response. Show both
   components in the row so the total is auditable.

5. **i18n.** New `affordability` namespace in
   `src/messages/{en,et,ru}.json`; keys symmetric across locales; no
   hardcoded user-facing strings. Reuse the existing room-category labels
   from the `housing` namespace rather than duplicating them.

6. **e2e.** Extend the calculator smoke: after the €3,000 / 2% submit,
   assert the affordability panel renders with at least one district and
   that moving the share control changes the district list.

## Non-goals

- No backend changes; no new API fields; no new dependencies.
- No map, chart, or trend UI (backlog).
- No URL state on the calculator — T20 owns that and runs after you.
  Keep the share control in local state; do not reach for the query
  string.
- No changes to the basis toggle, the constraint rendering, or the
  results cards T17 built. You are adding a panel below them.
- No changes outside the files listed below.

## Files you own

`frontend/src/app/[locale]/calculator/page.tsx` (the housing fetch and
the new prop only), a new affordability component under
`frontend/src/features/tax-calculator/components/`, the render call that
mounts it inside the existing results view, the `affordability`
namespace in `frontend/src/messages/*.json`, and
`frontend/e2e/smoke.spec.ts`.

Reuse types from `frontend/src/types/api.ts` — do not duplicate or
extend them.

## Acceptance criteria

- [ ] `npm run build` passes; no `any`.
- [ ] With both endpoints up: submit €3,000 / 2% → the panel shows the
      named source regime, the budget, and ≥1 affordable district,
      localized in en/et/ru.
- [ ] Switching the comparison basis changes the budget, and the panel's
      attribution line changes with it.
- [ ] Moving the share control updates the budget and the district list
      live.
- [ ] Districts are matched against rent + utilities, and both figures
      are visible per row.
- [ ] Backend fully down: the calculator page stays 200, the panel is
      absent, nothing crashes.
- [ ] `npm run e2e` passes including the extended smoke.
- [ ] `'use client'` count grows only inside `features/tax-calculator/`.

## Verification

- `cd frontend && npm run build && npm run e2e` (backend on :8000,
  compose db seeded).
- Commit: `feat(calculator): affordability panel linking net income to
  district rents`.

## On completion

Set T14 to `[R]` in `TODO.md` + a journal entry: what you verified, how,
and which regime the panel attributes the budget to under each basis.
