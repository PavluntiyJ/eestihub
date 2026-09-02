# T17 — Tax engine correctness pass

**Read first:** `docs/CONTEXT.md` (§4–§6, and §5 in full — it was
rewritten on 2026-09-02 specifically for this task).
**Dependencies:** none. **Role:** Full-stack.
**Branch:** work in `main`.
**Blocks:** T14, T20 (both touch `features/tax-calculator/`).

## Context

The 2026 tax constants in `tax_rates.py` are correct and sourced. The
arithmetic around them is not. An orchestrator audit found three defects
that make the calculator give wrong or misleading answers; this task
fixes all three plus the statutory limits nobody is told about, and
locks the result behind a golden-file suite so the next rate change is a
reviewable diff instead of a scavenger hunt.

The four defects, with the audit finding IDs:

- **F-01** `calculate_juhatuse_liige()` never withholds the II pension
  pillar contribution. It does not even accept `pension_pillar_rate`.
  Funded-pension contributions *are* withheld from board-member fees;
  only unemployment insurance is exempt. At €3,000 / 2% the API returns
  a net of €2,494.00 where €2,447.20 is correct.
- **F-02** All four regimes are computed from the same gross and then
  ranked by net, but the same gross costs the payer €4,014 / €3,990 /
  €3,000 / €3,000. The ranking is between incommensurable numbers.
- **F-03** FIE social tax is a flat 33% with no floor and no ceiling.
  The statutory monthly minimum (kuumäär × 33%) and the annual cap both
  apply.
- **F-04** The €40,000 ettevõtluskonto ceiling and the €40,000 VAT
  threshold are documented in CONTEXT and never surfaced to the user.

CONTEXT §5 has already been corrected for all of the above — the
contract there is authoritative, not a proposal. Implement it as written.

## Steps

1. **Verify the new constants (mandatory, T03 discipline).** Check
   against emta.ee and record the source URL and retrieval date in a
   comment next to each, exactly like the existing constants:
   - social tax monthly rate (`kuumäär`) for 2026 — the orchestrator read
     €886, giving a €292.38 monthly minimum obligation; confirm both;
   - the annual ceiling on FIE social tax for 2026 — derived from the
     minimum wage, and the figure moved for 2026. If no primary source
     states it for 2026, **stop and record the blocker in `TODO.md`**
     rather than inventing a number; implement the floor, ship the cap
     behind a clearly-named constant set to `None`, and say so;
   - the €40,000 entrepreneur-account registration threshold;
   - the €40,000 VAT registration threshold.
   All of them go in `backend/app/core/tax_rates.py`. No magic numbers
   in services (CONTEXT §4).

2. **F-01 — juhatuse liige.** Give `calculate_juhatuse_liige()` a
   `pension_pillar_rate` parameter, withhold the contribution, and make
   the income tax base `gross − pension − basic exemption`. Add a
   `pension_pillar_ii` line to its `breakdown`. Update
   `compare_regimes()` to pass the rate. Fix
   `tests/test_tax_service.py::test_juhatuse_liige` — its current
   expectation of €2,494.00 is the bug, not the baseline.

3. **F-03 — FIE bounds.** Clamp the FIE social tax between the monthly
   minimum obligation and the monthly share of the annual cap, then run
   the existing income tax step on the clamped figure.
   `test_fie_below_basic_exemption_after_social_tax` currently asserts
   €165.00 of social tax on €500 of income; the legal minimum is
   €292.38 and the test must be corrected, not deleted.

4. **F-04 — constraints.** Add `constraints: list[Constraint]` to
   `RegimeResult` (always present, may be empty) with the four codes and
   severities defined in CONTEXT §5. Machine keys only — no human text
   crosses the API (§6). Emit them per regime:
   - `ettevotluskonto_annual_limit_exceeded` — ettevõtluskonto only;
   - `vat_registration_threshold_exceeded` — fie and ettevõtluskonto only;
   - `fie_social_tax_minimum_applied` / `fie_social_tax_cap_applied` —
     whichever bound actually bound.

5. **F-02 — comparison basis.** Add `equalize_by: "gross" | "payer_cost"`
   to `TaxCalculationRequest`, defaulting to `"gross"` so existing
   callers are unaffected. Under `"payer_cost"`, derive each regime's own
   gross from the payer cost using the four formulas in CONTEXT §5, then
   run the unchanged per-regime math on it. `employer_total_cost` and
   `gross_income` in each result report the actual figures used.
   Keep the derivation in `tax_service.py`; the route stays thin.

6. **Golden-file regression suite.** Add
   `backend/tests/data/tax_golden.csv` with header
   `gross_monthly_income,pension_pillar_rate,equalize_by,regime,expected_net_income,expected_effective_tax_rate`
   and a `pytest.mark.parametrize` test that reads it and checks every
   row. Cover at minimum: the €3,000 / 2% case on both bases; a low
   income that triggers the FIE floor; an income above the basic
   exemption threshold and one below it; each pension rate at least once;
   an ettevõtluskonto income above €40,000/year. Derive the expected
   values by hand and keep the derivation in a comment column or an
   adjacent `README.md` — the point is that a future rate change shows up
   as a readable diff.

7. **Frontend — types.** Mirror the schema changes into
   `frontend/src/types/api.ts` 1:1, snake_case (§4). No `any`.

8. **Frontend — UI.** In `features/tax-calculator/`:
   - a control for the comparison basis (two options, labelled from the
     dictionaries), wired to `equalize_by`, defaulting to `gross`;
   - the results header states which basis is active, so the "Best net"
     badge is never unqualified again;
   - constraints render per result card: `blocker` visually distinct from
     `warning` from `info`, all text from the dictionaries by code;
   - **F-16, same file, fix it here:** `Number(grossIncome)` turns
     `"3000,50"` into `NaN` and silently disables the submit button.
     Estonian and Russian both use the comma as decimal separator, i.e.
     two of the three supported locales. Normalise the separator before
     parsing.

9. **i18n.** Extend the existing `calculator` namespace only — basis
   labels, the active-basis line, and one key per constraint code, with
   its severity styling driven by the API field, not by the key. Keys
   symmetric across `en`/`et`/`ru`. No hardcoded user-facing strings.

10. **e2e.** Extend the calculator smoke: submit on `payer_cost` and
    assert the ranking differs from the `gross` result; submit a €5,000
    income and assert the ettevõtluskonto blocker constraint renders.

## Non-goals

- No OÜ / dividends regime, no tax-residency switch, no health-insurance
  eligibility panel (all backlog for iteration 8).
- No year switcher; 2026 rates only.
- No URL state on the calculator (T20 owns that).
- No affordability panel (T14 owns that).
- No changes to housing, e-Residency, `layout.tsx`, `globals.css`, or
  any page shell under `app/[locale]/` — T18 and T19 are working there
  in parallel.
- Do not rename `employer_total_cost`. CONTEXT documents its meaning;
  renaming it breaks the type mirror and the e2e suite for no gain.

## Files you own

`backend/app/core/tax_rates.py`, `backend/app/services/tax_service.py`,
`backend/app/schemas/taxes.py`, `backend/app/api/v1/routes/taxes.py`,
`backend/tests/test_tax_service.py`, `backend/tests/test_taxes_api.py`,
`backend/tests/data/`, `frontend/src/types/api.ts`,
`frontend/src/features/tax-calculator/`, `frontend/e2e/smoke.spec.ts`,
and the `calculator` namespace inside `frontend/src/messages/*.json`.

Nothing else. If a fix seems to require another file, write it into
"Notes for the orchestrator" instead.

## Acceptance criteria

- [ ] `cd backend && pytest` green, golden-file suite included.
- [ ] Every new constant carries a source URL and retrieval date.
- [ ] `POST /api/v1/calculate-taxes` with `{"gross_monthly_income": 3000,
      "pension_pillar_rate": 0.02}` returns juhatuse liige
      `net_income: 2447.20` and a `pension_pillar_ii` breakdown line.
- [ ] The same request with `"equalize_by": "payer_cost"` returns
      ettevõtluskonto as the highest net, and every regime's
      `employer_total_cost` equals 3000.
- [ ] A request omitting `equalize_by` behaves exactly as before this
      task, except for the F-01/F-03 corrections.
- [ ] `{"gross_monthly_income": 5000}` returns the ettevõtluskonto
      blocker constraint; `{"gross_monthly_income": 500}` returns
      `fie_social_tax_minimum_applied`.
- [ ] `cd frontend && npm run build` passes; no `any`.
- [ ] Typing `3000,50` into the income field produces a calculation in
      all three locales.
- [ ] `npm run e2e` passes including the two new assertions.
- [ ] `'use client'` count grows only inside `features/tax-calculator/`.

## Verification

- `cd backend && pytest`; uvicorn + curl per CONTEXT §7.
- `cd frontend && npm run build && npm run e2e` (backend on :8000,
  compose db seeded).
- Commits: `fix(taxes): withhold II pillar for board members and bound
  FIE social tax` + `feat(taxes): comparison basis and statutory
  constraints` + `feat(calculator): basis toggle and constraint
  warnings`.

## On completion

Set T17 to `[R]` in `TODO.md` + a journal entry. State explicitly which
constants you verified, against which URL, on which date — and if the
FIE annual cap could not be sourced, say so in "Notes for the
orchestrator" so T14 is not planned against a number that does not exist.

---

## Rework — round 1 (orchestrator review, 2026-09-02)

Everything else is accepted: 41 tests pass, the build is clean, i18n is
at 100/100 parity with real translations, and every constant was verified
against a primary source — including the FIE annual ceiling of
€36,867.60, which the brief flagged as possibly unsourceable and which
you correctly found on the EMTA FIE social-tax page. The golden-file
derivations were re-checked by hand and are right.

One defect, introduced by this task, has to be fixed before acceptance.

**The FIE bar renders full-width when net income is negative.**

The statutory minimum social tax (€292.38) is owed regardless of income,
so below roughly €886/month of business income the FIE net goes negative.
That arithmetic is correct and must not change. The rendering is not:

```
POST /api/v1/calculate-taxes  {"gross_monthly_income": 200}
  → fie net_income = -92.38, effective_tax_rate = 1.462
```

In `ResultsView`:

```tsx
const width = bestNetIncome > 0 ? `${(result.net_income / bestNetIncome) * 100}%` : "0%";
<div className="h-full rounded-full bg-primary" style={{ width }} />
```

A negative net produces `width: -46.19%`. That is an invalid CSS value,
so the browser drops the declaration and the inner div falls back to
`width: auto` — which, as a block child, means 100% of its parent. The
worst regime on the board therefore renders as a full-length bar and
reads as the best one. Before this task FIE net could never be negative,
so the clamp is what exposed it.

Fix all three of these:

1. Clamp the bar width to a non-negative range so a negative net can
   never produce a longer bar than a positive one.
2. Give a negative net a distinct visual treatment — it is a real and
   meaningful outcome ("this regime costs you money at this income"),
   not an error state. Do not hide the regime and do not clamp the
   *number* to zero; only the bar geometry is wrong.
3. `effective_tax_rate` of 1.462 currently renders as "146.2%", which is
   arithmetically what the contract defines but reads as a glitch. Either
   suppress the metric when net income is negative or label it so the
   figure is legible. Your call — say which you chose and why.

Add a golden-file row at €200 / 0% covering the negative FIE net, and an
e2e assertion that the FIE bar is not the longest at that income.

**Non-blocking, do not fix here** — recorded so they are not lost:
`grossIncome.replace(",", ".")` replaces only the first comma, so
`"1,234,50"` or `"1 234,56"` still parse to `NaN`; `min` and `step`
remain on an input that is now `type="text"` and are inert;
`CONSTRAINT_STYLES` uses raw Tailwind palette colours rather than the
design tokens, which works but sits outside the token system — the
orchestrator has routed that one to T19.

## On completion of rework

Keep the status at `[>]` while you work, set `[R]` again when done, and
add a second journal entry stating what you changed and how you verified
the €200 case in a browser.
