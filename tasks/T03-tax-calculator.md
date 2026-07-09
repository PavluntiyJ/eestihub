# T03 — Tax calculation service + POST /api/v1/calculate-taxes

**Read first:** `docs/CONTEXT.md` (sections 4, 5 — contract and tax
logic). **Dependencies:** T02 accepted. **Role:** Backend (Python),
careful math required.

## Goal
A `POST /api/v1/calculate-taxes` endpoint that compares 4 Estonian tax
regimes for a given gross income. Request/response contract — strictly
per CONTEXT.md §5.

## Steps

1. **Verify the rates.** Check current 2026 rates on emta.ee (income
   tax, social tax, unemployment insurance, basic exemption,
   ettevõtluskonto rates). Put all constants in
   `app/core/tax_rates.py` with a source comment (URL + check date).
   No numbers anywhere else.
2. `app/schemas/taxes.py`: Pydantic schemas `TaxCalculationRequest`,
   `TaxCalculationResponse`, `RegimeResult`, `TaxLine` — fields per the
   contract. Validation: `gross_monthly_income > 0`,
   `pension_pillar_rate` from the allowed set.
3. `app/services/tax_service.py`: pure calculation functions, one per
   regime (`calculate_tooleping`, `calculate_juhatuse_liige`,
   `calculate_fie`, `calculate_ettevotluskonto`) + a
   `compare_regimes()` aggregator. Use `Decimal` for money, round to 2
   places ROUND_HALF_UP only at the output. Apply the basic exemption in
   income tax. For ettevõtluskonto compute annual turnover as
   `gross_monthly_income * 12` for rate determination.
4. `app/api/v1/routes/taxes.py`: thin route, mount into the v1
   aggregator.
5. **Tests** `tests/test_tax_service.py` + `tests/test_taxes_api.py`:
   - 1–2 tests per regime with hand-calculated expected values (the
     derivation in a comment);
   - edge cases: income below the basic exemption; ettevõtluskonto above
     the annual threshold; `pension_pillar_rate = 0`;
   - API test: 422 on negative income.
6. Commit: `feat(backend): estonian tax comparison service and endpoint`.

## Non-goals
- Do not touch the frontend.
- Do not over-engineer: no FIE social tax cap, no progressive exemption
  phase-out — the simplifications are recorded in CONTEXT.md §5. If you
  find a real-world discrepancy that breaks a simplification, write it
  to "Notes for the orchestrator" in TODO.md.

## Acceptance criteria
- [ ] `pytest` green; tests cover all 4 regimes and edge cases.
- [ ] `curl -X POST localhost:8000/api/v1/calculate-taxes` with the
      CONTEXT.md example returns 4 results matching the hand
      calculation.
- [ ] All math in the service, thin route, rates only in `tax_rates.py`.
- [ ] Every rate in `tax_rates.py` has a source and check date.

## On completion
Set T03 to `[R]` in `TODO.md`; put the pytest output and a sample API
response in the journal.
