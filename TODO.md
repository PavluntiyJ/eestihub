# TODO — EestiHub task board

Statuses: `[ ]` not started · `[>]` in progress · `[R]` in review with the orchestrator · `[x]` accepted

Rules for workers:
1. Before starting, read `docs/CONTEXT.md` and your task file in `tasks/`.
2. Taking a task — set `[>]` and fill in the worker. Finished — `[R]` + a journal entry.
3. Only the orchestrator sets `[x]`, after review.
4. Stay within the task scope. Spotted an out-of-scope problem — write it to "Notes for the orchestrator", do not fix it yourself.

## Iteration 1 — MVP skeleton (closed 2026-07-09)

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T01 | Monorepo scaffold: git, folders, docker-compose, configs | tasks/T01-scaffold.md | `[x]` | gpt-5.5 | — |
| T02 | FastAPI skeleton + GET /api/v1/health | tasks/T02-backend-skeleton.md | `[x]` | gpt-5.5-codex | T01 |
| T03 | Tax calculation service + POST /api/v1/calculate-taxes + tests | tasks/T03-tax-calculator.md | `[x]` | gpt-5.5-codex | T02 |
| T04 | Base Next.js page with a backend fetch | tasks/T04-frontend-base.md | `[x]` | gpt-5.5-codex | T02 |

## Iteration 2 — features (closed 2026-07-09)

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T05 | Housing API (mock data) + rent dashboard | tasks/T05-housing-dashboard.md | `[x]` | gpt-5.5 | T03, T04 |
| T06 | Tax calculator UI (form + infographic) | tasks/T06-calculator-ui.md | `[x]` | gpt-5.5 | T03, T04 |
| T07 | Header navigation to /calculator and /housing | tasks/T07-header-nav.md | `[x]` | gpt-5.5 | T05, T06 |

## Iteration 3 — DB and e2e (closed 2026-07-09)

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T08 | Housing from Postgres: SQLAlchemy model + idempotent seed | tasks/T08-housing-postgres.md | `[x]` | gpt-5.5 | T05 |
| T09 | Playwright e2e smokes for the key flows | tasks/T09-e2e-smoke.md | `[x]` | gpt-5.5 | T07 |

## Iteration 4 — launch prep (started 2026-07-09)

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T10 | CI on GitHub Actions (pytest + build + e2e) | tasks/T10-ci.md | `[x]` | gpt-5.5 | T09 |
| T12 | Calculator disclaimer + site footer | tasks/T12-disclaimer-footer.md | `[x]` | deepseek | T06, T07 |
| T11 | README + MIT license + SEO (x-default, sitemap, robots, OG) | tasks/T11-readme-seo.md | `[x]` | deepseek-pro-v4 | T10, T12 |

## Iteration 5 — deploy (closed 2026-07-09)

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T13 | Deploy config: Render blueprint, keep-alive, runbook | tasks/T13-deploy.md | `[x]` | deepseek-pro-v4 | T11 |

## Iteration 6 — usefulness pass (superseded 2026-09-02)

Planned 2026-08-23 with T14–T16. None of the three was ever assigned or
started, and the 2026-09-02 audit changed the ordering: correctness work
has to land before anything is built on top of the calculator's numbers.
All three tasks moved into iteration 7 — T15 and T16 unchanged apart from
small review amendments, T14 rebased onto T17.

## Iteration 7 — audit remediation + usefulness (closed 2026-09-02, all 7 tasks accepted)

Full audit with evidence for every finding ID below:
https://claude.ai/code/artifact/1eeb632e-3479-45fd-831e-427ab2433192

**Wave 1 — start these four in parallel, they share no files:**

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T17 | Tax engine correctness: II pillar for board members, comparison basis, FIE bounds, constraints, golden files | tasks/T17-tax-engine-correctness.md | `[x]` | gpt-5-codex | — |
| T18 | Production hardening: pooling, real health check, static rendering, absolute SEO URLs | tasks/T18-production-hardening.md | `[x]` | gpt-5.6-sol | — |
| T15 | Housing real data: snapshots, ingest, trends API | tasks/T15-housing-real-data.md | `[x]` | gpt-5.6-sol | — |
| T16 | e-Residency first-year cost calculator | tasks/T16-eresidency-calculator.md | `[x]` | gpt-5.6-sol | — |

**Wave 2 — after their dependencies are `[R]`:**

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T19 | Frontend polish: typeface, dark mode, error boundaries, OG images | tasks/T19-frontend-polish.md | `[x]` | claude-opus-5 | T18 |
| T14 | Affordability link: net income → affordable districts (rebased) | tasks/T14-affordability-link.md | `[x]` | claude-opus-5 | T17 |

**Wave 3:**

| # | Task | Brief | Status | Worker | Depends on |
|---|------|-------|--------|--------|------------|
| T20 | Shareable calculator scenario URLs | tasks/T20-shareable-scenarios.md | `[x]` | claude-opus-5 | T17, T14 |

Findings covered: T17 → F-01 F-02 F-03 F-04 F-16 · T18 → F-05 F-06 F-07
F-08 F-09 F-17 · T19 → F-10 F-11 F-13 F-14 · T20 → F-15 F-20.
Still open after this iteration: F-12 (Recharts payload) and F-18
(no Python lint/type gate) — backlog, see Notes.

Each brief carries a "Files you own" section. It is binding: three
deliberate overlaps were resolved when the slate was drafted — T16 is the
sole owner of `sitemap.ts`, T18 touches only `HealthResponse` inside
`types/api.ts`, and T15 must not touch the `/rents` handler that T18
edits. Shared `messages/*.json` follows the standing rule: each task adds
only its own namespace.

## Journal (newest first)

- 2026-09-02 · claude-opus-5 (orchestrator, acting as worker) · **T20 done —
  iteration 7 closed, all seven tasks `[x]`.** Same caveat as wave 2: I wrote
  this code and accepted it, so it has had no independent review.

  **URL contract, recorded verbatim as the brief requires** — the future
  programmatic-SEO task must be written against exactly this:
  - `gross` — monthly amount. Accepts a comma decimal separator; written back
    normalised with a dot. Invalid or absent → `3000`.
  - `pillar` — whole percent, one of `0` `2` `4` `6` (not `0.02`). Anything
    else → `2`.
  - `basis` — `gross` or `payer_cost`, mirroring the API's `equalize_by`.
    Anything else → `gross`.
  - All three are optional. Results only render when `gross` is present *and*
    valid; every other combination shows the empty state, never an error.
  Parsing and serialisation live in `features/tax-calculator/scenario.ts` so
  the server page and the client form cannot drift apart.

  · **Deviated from the brief on one point, deliberately.** The brief said
  `router.replace`, reasoning that push would make the back button walk through
  every keystroke. That reasoning does not apply to this implementation: only a
  submit writes to the URL, editing fields does not. With `replace`, back would
  have skipped past every scenario the user submitted — which contradicts the
  brief's own acceptance criterion. Used `push`, and added a render-phase state
  sync so a back/forward navigation adopts the incoming scenario while the
  server render caused by our own submit does not clobber the result the client
  already computed. Covered by a new e2e assertion.
  · **F-20.** The language switcher now carries the query string and the hash.
  `useSearchParams` forced a Suspense boundary around it in the header;
  verified afterwards that every page still builds as `●`.
  · **Worth noting:** `/[locale]/calculator` reads `searchParams` and still
  prerenders as `●` — Next serves the static shell and renders the
  query-dependent part per request. So T18's F-09 win survived and a shared
  link still arrives with its numbers in the HTML; no trade-off was needed.
  · Verified: `npm run build` clean with no lint warnings; i18n parity 155/155;
  `npm run e2e` → 15 passed; `curl` on
  `?gross=3000&pillar=2&basis=payer_cost` returns four server-rendered result
  cards with the payer-cost figures (€1,839.92 / €1,878.21 / €1,721.80 /
  €2,340.00), the bare URL returns none, and `?gross=abc&pillar=99` returns 200
  with the default form; copy-link verified through the real clipboard API;
  with the backend stopped the scenario URL still returns 200 with a usable
  form and no results.

  · **Iteration 7 result.** 18 of the 20 audit findings are closed. F-12
  (Recharts payload) and F-18 (no Python lint/type gate) remain open by
  decision, plus F-19 (e2e assert on English copy) and the three items added to
  Notes during wave 2. Next candidates, in the order I would take them: OÜ with
  a salary/dividend split, health-insurance eligibility per regime, and the
  tax-residency switch — the three that make the calculator authoritative for
  the audience the homepage actually addresses.

- 2026-09-02 · claude-opus-5 (orchestrator, acting as worker) · **Wave 2 done:
  T19 and T14 both `[x]`.** The owner directed me to implement these directly
  because the worker was out of budget, so CLAUDE.md's "orchestrator does not
  write application code" was waived for this pass. Flagging the obvious
  caveat: nobody independently reviewed this code the way I reviewed wave 1.
  · **T19.** F-10 fixed — `--font-sans` was defined as itself; it now resolves
  to `var(--font-geist-sans)` with a real fallback stack, verified in the built
  CSS (`font-family:var(--font-geist-sans),ui-sans-serif,system-ui,sans-serif`,
  zero self-references). F-11 — three-state theme control (light/dark/system)
  in the header, persisted in localStorage, applied by an inline pre-paint
  script so there is no flash. Two mistakes worth recording: Next silently
  strips scripts from a hand-written `<head>`, so it had to move to the top of
  `<body>`; and the storage key was exported from a `"use client"` module,
  which made the server render `localStorage.getItem(undefined)` — constants
  shared with a server component must live in a plain module, now
  `src/lib/theme.ts`. F-13 — localized `error.tsx`, `not-found.tsx` and
  `loading.tsx`. F-14 — `opengraph-image.tsx` per locale via `next/og`,
  prerendered, inherited by every child route; checked the rendered PNG.
  · **T19 criterion NOT met, deliberately.** The brief asked that `/xx` render
  the localized not-found inside the site shell. The only way to route unmatched
  URLs into `[locale]/not-found.tsx` is a `[...rest]` catch-all — I built it,
  and it returns **HTTP 200**, because the layout has already flushed the
  response head before `notFound()` throws. Worse, the next-intl middleware then
  emits `hreflang` alternates for the nonexistent path, telling Google that
  `/en/nope`, `/et/nope` and `/ru/nope` are three translations of a real page.
  A soft-404 farm on an SEO-focused site is worse than an unstyled 404, so I
  reverted the catch-all. Unmatched URLs keep Next's default page with a correct
  404; the localized not-found still serves genuine `notFound()` calls. Proper
  fix needs a root layout — logged in Notes.
  · **T14.** Rebased as briefed: the budget comes from the top-ranked regime
  under the active comparison basis and the panel names that regime, the 30%
  factor is a slider (15-50%), and districts are matched on rent **plus**
  utilities with both components shown. Rents are fetched server-side with a
  one-day revalidate, so the calculator stays statically rendered and T18's
  F-09 win is preserved. Verified the offline rule the hard way: built with the
  backend down, then loaded the page with the API back up — 4 result cards
  render, the panel is absent, no page errors.
  · **Stale copy fixed, outside both briefs.** `housing.mockNote` still said
  "demo (mock) values and does not reflect the real Tallinn rental market" and
  the footer said "demo housing data". After T15 that is simply false, and it
  told users the sourced numbers were fake. Rewritten in all three locales to
  describe what the figures actually are: midpoints of published district
  ranges, with utilities as a separate estimate.
  · Verified: `npm run build` clean, all locale routes still prerendered;
  i18n parity 153/153 across en/et/ru; `npm run e2e` → 11 passed against a live
  backend serving real snapshot data; panel screenshotted in both themes and
  the two affordable districts at 30% (Mustamäe €690, Lasnamäe €675) match a
  hand calculation from the source data.
  · T20 is now unblocked.

- 2026-09-02 · claude-opus-5 (orchestrator) · **Wave 1 accepted: T15, T16,
  T17, T18 all `[x]`.** The worker ran out of budget with the code finished
  but uncommitted; this entry covers the review, the gap I closed, and the
  commits.
  · Independently verified rather than taken on trust: `pytest` → 55 passed;
  production build clean with every locale route now prerendered (`●`), which
  closes F-09; live API run against a throwaway SQLite DB — health
  `{"status":"ok","database":"ok"}` 200, rents carrying
  `Cache-Control: public, max-age=86400, stale-while-revalidate=604800` and
  `updated_at: 2026-05-27` with snapshot-backed values, trends returning eight
  ordered series; ingest run twice → 8 snapshot rows, idempotency holds;
  `npm run e2e` → 10 passed against that live backend.
  · **T15's data source was checked at the primary source, not accepted from
  the brief.** The Hinnapäring 2026 district report exists, is dated
  2026-05-27, and attributes its figures to Ruumiamet transaction statistics
  plus a KV.ee/City24 offer analysis. All 24 published ranges were re-derived
  by hand: every CSV value is the correct integer midpoint. `avg_utilities` is
  deliberately left empty because the source does not publish it — the trends
  API reports null and only the rents API substitutes the legacy estimate.
  That is the right call and must not be "tidied up" later.
  · T16's fee constants and T17's tax constants all carry source URLs with
  retrieval dates; the e-Residency worked example in CONTEXT §5 was generated
  from the real service and matches byte for byte.
  · **Gap I found and fixed — it fell between two briefs, so it is my
  miss, not a worker's.** T15 creates and populates `rent_snapshots` locally,
  but `render.yaml`'s start command ran only `scripts.seed_housing`, and the
  CI e2e job did the same. `create_all` would have made the table in
  production and left it empty, so the deployed dashboard would have silently
  fallen back to the 2026-07-01 mock values — T15 shipping without reaching
  production at all. Added `python -m scripts.ingest_rents` to both the Render
  start command and the CI e2e job; the script is idempotent, so running it on
  every boot is safe. T15 was scoped backend-only and T18 owned `render.yaml`
  without reason to know about the new script — the seam was in how I split
  the briefs.
  · CONTEXT §5 updated with the three contract additions the workers correctly
  flagged for orchestrator review: `HealthResponse.database` with the 503
  policy, `GET /api/v1/housing/trends`, and `POST /api/v1/calculate-eresidency`
  (explicitly documented as a cost model that does not tax the revenue), plus
  the `updated_at` semantics and cache header on rents.
  · Wave 2 is now unblocked: T19 (depends on T18) and T14 (depends on T17) can
  both start; T20 follows T14.

- 2026-09-02 · gpt-5.6-sol · T18 done: made SQLAlchemy engine/session
  creation lazy while preserving the seed script's existing imports, enabled
  `pool_pre_ping` with a 300-second recycle window, changed health to query the
  database, cached successful rents responses, split runtime/test Python
  dependencies, added a default overridable frontend request timeout, moved
  the landing status check into a client leaf, enabled locale prerendering and
  absolute metadata URLs, and gave housing data a one-day revalidation window.
  `HealthResponse` now includes `database: "ok" | "unavailable"`; only that
  type was touched in the shared `frontend/src/types/api.ts`, and CONTEXT §5
  needs the orchestrator's contract update. Chosen health policy: return 503
  only while the database query fails (`degraded`/`unavailable`), so Render's
  existing health path detects an actual dependency outage; tax calculations
  remain 200 because they do not use the database, and pooled connections
  recover without a process restart. Production build route table:
  ```text
  ○ /_not-found
  ● /[locale]                 /en /et /ru
  ● /[locale]/calculator      /en/calculator /et/calculator /ru/calculator
  ● /[locale]/eresidency      /en/eresidency /et/eresidency /ru/eresidency
  ● /[locale]/housing         /en/housing /et/housing /ru/housing
  ○ /robots.txt
  ○ /sitemap.xml
  ```
  (`●` is Next.js static HTML generated from `generateStaticParams`; housing
  retains `force-dynamic` and emits no `housing.html`.) Built head contains
  `<link rel="canonical" href="https://eestihub.vercel.app/en"/>` and
  `<link rel="alternate" hrefLang="et" href="https://eestihub.vercel.app/et"/>`.
  Verified: clean venv install from `requirements.txt` +
  `requirements-dev.txt`; `pytest` → 55 passed; production build passed;
  backend fully down → `/en` 200 in 48 ms and browser offline state in 127 ms;
  rents 200 with `Cache-Control: public, max-age=86400,
  stale-while-revalidate=604800`; malformed `DATABASE_URL` import succeeded;
  a deliberately stale pooled connection recovered without restarting
  (`pre_ping=True`, `pool_recycle=300`); e2e → 10 passed against isolated
  seeded SQLite. The exact compose stop/start cycle could not run because this
  worker environment has neither Docker nor Podman; no shared DB state was
  changed. T16 changed `sitemap.ts` concurrently; T18 did not touch it.

- 2026-09-02 · gpt-5.6-sol · T16 done: added the sourced e-Residency fee
  table, Decimal-based first-year cost service and
  `POST /api/v1/calculate-eresidency`; built a localized en/et/ru
  calculator with setup, running-cost, revenue, surplus and break-even
  results; added navigation, relative page alternates, a 12-URL sitemap
  with `x-default` and `lastModified`, and a browser smoke. Verified the
  EUR 150 application/renewal fee, EUR 265 online OÜ registration,
  EUR 200-400 annual contact-person range and accounting from EUR 50
  against the official e-Residency Knowledge Base and 2026 Q&A; checked
  current EUR 50-100 small-company accounting offers in the official
  marketplace and the online/notary alternatives against the e-Business
  Register and Chamber of Notaries, all retrieved 2026-09-02. Verification:
  `pytest` → 55 passed; live API → 200 for a valid request and 422 for an
  invalid request; `npm run build` passed with all three pages statically
  rendered; live hreflang and sitemap counts checked; `npm run e2e` → 10
  passed using the project's seeded SQLAlchemy model with temporary SQLite.
  The new API contract must still be reviewed into CONTEXT §5 by the
  orchestrator.

- 2026-09-02 · gpt-5.6-sol · T15 done: added the `rent_snapshots`
  history model and unique idempotency key, an idempotent standard-library
  CSV ingest command, a dated all-eight-district snapshot, per-district
  latest-snapshot selection with legacy rent/utility fallback, and an
  ordered trends API. The public Hinnapäring 2026 district/room ranges,
  their integer-midpoint transformation, retrieval date, provenance and
  reuse caveat are documented in `backend/scripts/data/SOURCES.md`; no
  listings were scraped. Contract additions proposed for CONTEXT §5:
  (1) rents `updated_at` is the maximum real `captured_on` when snapshots
  exist; (2) `GET /api/v1/housing/trends` returns
  `{city, districts: [{name, points: [{captured_on, avg_rent_1room,
  avg_rent_2room, avg_rent_3room, avg_utilities, source}]}]}`, with
  districts and points in ascending order. Left T18's `/housing/rents`
  handler unchanged and added only the trends route/imports in its shared
  file. Deployment note: Render's existing start command runs
  `scripts.seed_housing`, whose `Base.metadata.create_all()` now sees
  `RentSnapshot` through the housing-model import and creates the absent
  table on the next start without touching Neon data; `create_all` will
  not alter an existing table for future column changes, which would need
  explicit DDL or a migration tool. Verified: full backend pytest → 55
  passed; compileall and `git diff --check` clean; live SQLite seed plus
  ingest twice → 8 snapshots; live rents → snapshot values with
  `updated_at: 2026-05-27`; trends → eight series; health and taxes → 200.
  With an unreachable PostgreSQL URL, rents/trends → 503 and taxes → 200;
  health → T18's intentional 503 degraded response. Docker/Podman is not
  installed on this host, so the equivalent compose/PostgreSQL run could
  not be performed.

- 2026-09-02 · gpt-5-codex · T17 rework round 1 done: clamped every
  comparison-bar width to the 0–100% range; negative net income now has
  a destructive track marker, amount styling, result-card border and a
  localized badge instead of falling back to a full-width bar. Kept the
  negative monetary result unchanged and suppressed effective tax rate
  only for negative-net cards: the rate remains valid in the API/golden
  file, but showing 146.2% beside an explicit −€92.38 net adds confusion
  rather than information. Added the €200 / 0% FIE golden row and its
  hand derivation (`net = -92.38`, effective rate `1.462`), plus a browser
  assertion that the FIE fill is 0% while the best bar is 100%. Verified:
  `pytest tests/test_tax_service.py -q` → 32 passed; Playwright in real
  Chromium, `--grep "negative FIE net"` → 1 passed; the browser rendered
  the localized negative-net treatment and did not render `146.2%` in
  the FIE card. Commit: `aa30700`.

- 2026-09-02 · claude-opus-5 (orchestrator) · T17 reviewed, **returned
  for one narrow rework** — see the "Rework — round 1" section appended to
  `tasks/T17-tax-engine-correctness.md`. Status back to `[>]`.
  Independently verified rather than taken on trust: re-ran `pytest`
  (41 passed) and `next build` (clean); re-derived every golden-file row
  by hand (all correct, including both payer-cost derivations); confirmed
  i18n parity at 100/100 with genuine et/ru translations; and re-checked
  the constant the brief flagged as risky — €36,867.60 is indeed stated
  as the 2026 FIE annual social-tax ceiling on the cited EMTA page, so
  the worker sourced it correctly where the audit could not.
  F-01, F-02, F-03, F-04 and F-16 are all correctly implemented.
  · The defect: the FIE clamp makes net income negative below ~€886/month
  (€200 → −92.38), which is arithmetically right, but `ResultsView`
  computes the comparison bar as `net / bestNet` and hands the browser
  `width: -46.19%`. That is invalid CSS, so the declaration is dropped and
  the block-level bar falls back to `width: auto` = 100% — the worst
  regime renders as a full-length bar and reads as the best. Not
  reachable before this task, because FIE net could not previously go
  negative. Also `effective_tax_rate` 1.462 renders as "146.2%".
  · T14 and T20 stay blocked until this lands. T18, T15 and T16 are
  unaffected and can continue in parallel.
  · Routed to other tasks rather than to this one: the raw-Tailwind
  constraint colours bypass the design tokens (→ T19); the comma
  normalisation handles only the first separator (backlog).

- 2026-09-02 · gpt-5-codex · T17 done: corrected II-pillar withholding
  for board-member fees; added gross/payer-cost comparison bases, bounded
  FIE social tax, statutory constraints, a 20-row golden-file suite with
  documented hand derivations, mirrored frontend types, a localized basis
  selector and severity-styled constraint messages, comma-decimal parsing,
  and calculator e2e coverage. Verified the 2026 social-tax monthly rate
  (€886) and minimum (€292.38) against
  https://www.emta.ee/uudised/maksumuudatused-2026 and
  https://www.emta.ee/ariklient/maksud-ja-tasumine/tulumaks-ja-sotsiaalmaks/sotsiaalmaks;
  the FIE annual social-tax ceiling (€36,867.60) against
  https://www.emta.ee/ariklient/registreerimine-ettevotlus/ettevotjale/fuusilisest-isikust-ettevotjale-fie/sotsiaalmaks;
  the entrepreneur-account annual limit (€40,000) against
  https://www.emta.ee/eraklient/maksud-ja-tasumine/maksustatavad-tulud/ettevotluskonto;
  and the VAT registration threshold (€40,000) against
  https://www.emta.ee/ariklient/maksud-ja-tasumine/kaibemaks/kaibemaksukohustuslasena-registreerimine/maksukohustuslasena-registreerimise-kohustus,
  all retrieved 2026-09-02. Verification: `cd backend && pytest` → 41
  passed; live API curl checks matched €2,447.20 board-member net, equal
  €3,000 payer costs and both requested constraints; `cd frontend && npm
  run build` passed; `npm run e2e` → 8 passed. Docker/Postgres was not
  available locally, so the unchanged housing e2e prerequisite used the
  project's real SQLAlchemy model and seed against a temporary SQLite DB;
  all application API/browser paths were exercised and no project file was
  changed for that workaround.

- 2026-09-02 · claude-opus-5 (orchestrator) · Full audit of the codebase,
  deploy config and tax domain; owner approved the whole remediation
  slate. Method: read every backend/frontend/CI/deploy file, ran the
  backend suite (17 passed), ran a production frontend build and
  inspected its route table, emitted HTML and CSS directly, and
  re-verified all 2026 tax constants against emta.ee. 20 findings
  (F-01..F-20), report at
  https://claude.ai/code/artifact/1eeb632e-3479-45fd-831e-427ab2433192
  · **CONTEXT §5 rewritten** (orchestrator-only file) before any brief:
  the juhatuse liige II-pillar rule was wrong in the spec itself, not
  just in the code (F-01); FIE social tax now documented with its
  statutory floor and ceiling (F-03); added the `equalize_by` comparison
  basis with the four derivation formulas (F-02) and the `constraints`
  array with four defined codes (F-04); `employer_total_cost` documented
  as "payer cost" rather than renamed.
  · Wrote `tasks/T17..T20`, rebased `tasks/T14`, amended `tasks/T15`
  (migrations question at review, shared-route warning) and `tasks/T16`
  (sole ownership of `sitemap.ts`). Iteration 6 superseded — none of its
  three tasks had been assigned. Board reorganised into three waves with
  binding "Files you own" sections; the three real file overlaps between
  parallel tasks were resolved in the briefs rather than left to merge.
  · No application code touched. All statuses `[ ]` pending assignment.

- 2026-08-23 · gpt-5.6-sol · Owner approved the improvement brainstorm:
  drafted iteration 6 with briefs T14 (affordability link),
  T15 (housing snapshot history + trends API), T16 (e-Residency cost
  calculator). Created `tasks/T14..T16`, added the board section and the
  backlog to Notes. No application code touched; statuses left `[ ]`
  pending assignment. T15/T16 each propose API-contract additions that
  need an orchestrator review into CONTEXT §5 before acceptance.

- 2026-07-10 · orchestrator · Keep-alive removed (owner's decision: the cron spammed the Actions tab with failing runs and a warm backend isn't needed). Deleted `.github/workflows/keepalive.yml`; scrubbed references from README (deployment note + structure tree) and docs/DEPLOY.md (dropped the BACKEND_URL setup section, the keep-alive smoke check, and the 60-day scheduled-workflow caveat; renumbered smoke checks to section 5). The `BACKEND_URL` repo variable on GitHub is now unused and can be deleted in Settings → Actions → Variables (harmless if left). Consequence: Render Free cold start (~1 min) on the first request after 15 idle minutes — documented in README and DEPLOY.md caveats. Historical journal/brief mentions left as-is.
- 2026-07-09 · orchestrator · DEPLOYED TO PRODUCTION. ITERATION 5 CLOSED — the MVP is live: frontend https://eestihub.vercel.app (Vercel Hobby), backend https://eestihub-api.onrender.com (Render Free, Frankfurt), Postgres on Neon Free (eu-central-1, seeded — 8 rows verified by direct SQL). Executed via CLIs/APIs by the orchestrator with the owner doing browser logins (neonctl auth, vercel login) and providing a Render API key; one deviation from the runbook — Render now requires a card on file even for the free plan (owner added one; no charges on free). The Render service was created through the REST API with settings identical to render.yaml (the Blueprint itself was not applied — API path instead). Smoke checks all green: health 200; housing 8 districts from Neon; calculate-taxes €3000/2% → Tööleping net 2409.76; CORS preflight from the Vercel origin → allow-origin echoed; all pages 200 with the online badge; sitemap 9 URLs and robots on the prod domain; a real browser submit on the prod calculator (via the screenshots script) rendered results end-to-end (Vercel → CORS → Render → Neon); `BACKEND_URL` repo variable set, keep-alive dispatched and pinged Render successfully. README: live-demo links replace the placeholder; calculator/housing screenshots refreshed from prod. Post-deploy notes: the owner should ROTATE the Render API key (it transited the chat); Neon created the project on Postgres 17 vs compose's 16 — harmless for this app, alignment optional. The MVP roadmap is complete; anything further (real housing data, custom domain, analytics) is a new iteration on the owner's initiative.

- 2026-07-09 · orchestrator · T13 review: accepted `[x]`. Verified independently: commit scope exactly matches the acceptance criteria (render.yaml, keepalive.yml, DEPLOY.md, README, TODO — no app code, ci.yml, e2e or compose touched); both YAML files parse; no secrets committed (`sync: false` for DATABASE_URL/CORS_ORIGINS); the keep-alive skips with exit 0 when `vars.BACKEND_URL` is unset; DEPLOY.md runbook is complete and correctly ordered (Neon → Render → Vercel → CORS update → BACKEND_URL, smoke checks, free-tier caveats); README Deployment section + live-URL placeholder in place. Two fixes applied at review: `env: python` → `runtime: python` in render.yaml (the `env` field is deprecated in the current Blueprint spec — checked against Render docs) and a "psycopg2" → "psycopg" typo in DEPLOY.md (the project uses psycopg 3). Pushed; live CI + a manual keepalive dispatch (expect a green graceful skip) are the final gates. Review limitation: the Blueprint cannot be validated against Render without applying it — the owner's runbook execution is the real test; if Render rejects a field, it comes back as a fix task. Next: the owner executes docs/DEPLOY.md, then the orchestrator adds the live URL to the README and closes iteration 5.
- 2026-07-09 · deepseek-pro-v4 · T13 done: created `render.yaml` (Render Blueprint: web service `eestihub-api`, python, free/frankfurt, idempotent seed on boot, health check `/api/v1/health`, PYTHON_VERSION=3.12, DATABASE_URL/CORS_ORIGINS with sync:false); created `.github/workflows/keepalive.yml` (cron */10 + workflow_dispatch, skips gracefully with exit 0 when vars.BACKEND_URL is unset, green before first deploy); wrote `docs/DEPLOY.md` (step-by-step English runbook for Neon→Render→Vercel→CORS_ORIGINS update→BACKEND_URL, smoke checks, free-tier caveats including Render cold start ~1 min, Neon scale-to-zero, GitHub 60-day cron inactivity); added Deployment section to README linking to DEPLOY.md, plus a live-URL placeholder comment · Verified: both YAML files parse clean (Python yaml.safe_load); `cd frontend && npm run build` passes unchanged (regression guard); git diff scope matches acceptance criteria exactly — only render.yaml, .github/workflows/keepalive.yml, docs/DEPLOY.md, README.md, TODO.md; no changes to application code, ci.yml, e2e, or docker-compose. Commit: `ci: render blueprint, keep-alive ping and deploy runbook` (a9aec61).
- 2026-07-09 · orchestrator · ITERATION 5 STARTED (owner's decision: deploy on free tiers — Vercel Hobby for the frontend, Render Free for the backend, Neon Free for Postgres; accounts created). Free-tier picks verified against July 2026 sources: Koyeb dropped free compute for new accounts, Supabase free pauses projects after 7 idle days with manual unpause, Render's free Postgres expires after 90 days — hence Neon (scale-to-zero, sub-second resume). Known trade-off: Render cold start ~1 min, mitigated by a GitHub Actions keep-alive ping. ASSIGNMENT: T13 (tasks/T13-deploy.md) → any available worker, in `main`; repo-side files only (render.yaml, keepalive workflow, DEPLOY.md runbook, README section) — the owner executes the runbook in the dashboards, then the orchestrator adds the live URL to the README. Backend needed no code changes: DATABASE_URL/CORS_ORIGINS are already env-driven.

- 2026-07-09 · orchestrator · T11 review: accepted `[x]`. ITERATION 4 CLOSED — the project is ready for deploy. Verified independently: commit scope clean (two conventional commits, only README/LICENSE/screenshots/scripts + the four sanctioned frontend SEO files); `npm run build` clean with `/sitemap.xml` and `/robots.txt` as static routes; on a prod build + live backend — robots 200 (allow all + sitemap link), sitemap 200 with 9 URLs (3 pages × 3 locales) and per-URL alternates, hreflang with `x-default` → en on all three pages, OG title/description/type present and localized (checked en + ru); `npm run e2e` → 6 passed; MIT LICENSE correct; README commands match CONTEXT §7. One fix applied at review: the worker's screenshots were captured against the dev server and showed the Next.js dev-tools overlay bubble — re-captured by the orchestrator with the worker's own `frontend/scripts/screenshots.ts` against the prod build (content identical, overlay gone). Non-blocker: a Recharts tooltip freezes mid-chart on the housing fullPage screenshot (a known Playwright fullPage + Recharts hover artifact, not a code bug) — acceptable, revisit if screenshots are ever re-shot. Push + live CI run is the final gate. Next: deploy (owner's decision on the target platform).
- 2026-07-09 · deepseek-pro-v4 · T11 done: replaced README with full English product description, CI badge, features, screenshots, architecture, Getting started/testing sections with copy-paste commands from CONTEXT §7, project tree, license; captured 3 screenshots via a manual Playwright script `frontend/scripts/screenshots.ts` (en locale, 1280×800, light theme) → `docs/screenshots/{home,calculator,housing}.png`; added MIT LICENSE (Copyright (c) 2026 Pavel Jevstignejev); added x-default hreflang pointing to /en on all three pages and the layout; created `sitemap.ts` (all pages × locales, absolute URLs from `NEXT_PUBLIC_SITE_URL`, default `http://localhost:3000`) and `robots.ts` (allow all + sitemap link); added OG metadata (title/description from dictionaries, type website) in the layout; added `NEXT_PUBLIC_SITE_URL` to `frontend/.env.example` · Verified: `npm run build` clean (sitemap and robots generated as static routes); `curl /sitemap.xml` → 200, 9 URLs (3 pages × 3 locales) with alternates; `curl /robots.txt` → 200, allow all + sitemap link; hreflang includes x-default on /en, /en/calculator and /en/housing (verified via curl + grep on production HTML); OG title/description/type present on all pages; `npm run e2e` → 6 passed. Two commits: `docs: english readme with screenshots and mit license` (8188db1), `feat(frontend): sitemap, robots and x-default hreflang` (95ebfb2).
- 2026-07-09 · orchestrator · ASSIGNMENT: T11 (tasks/T11-readme-seo.md) → any available worker (owner's decision: no per-model assignment), work in `main`. Brief re-checked after the T10/T12 acceptances and the EestiHub rename — current, no edits needed. The worker sets `[>]` and fills in their name on taking the task. T11 is the last task before deploy.
- 2026-07-09 · orchestrator · BRAND RENAME (owner's decision): EstiHub → **EestiHub** — grammatically correct Estonian ("Eesti") and matches the repo name. Docs renamed by the orchestrator (CLAUDE.md, AGENTS.md, README.md, CONTEXT.md, this board, T12 brief); code strings (frontend dictionaries + the FastAPI title) added as step 0 of the not-yet-started T12, with a one-line backend exception. Infrastructure identifiers (`estihub` DB user/database in compose/.env) intentionally stay as they are. Naming rationale recorded: plain "Eesti" is the country name — unbrandable, clashes with the official eesti.ee state portal and is hopeless for SEO; the "Hub" suffix says what the product is.
- 2026-07-09 · orchestrator · T10 review: accepted `[x]`. Verified: workflow structure matches the brief (three jobs, pinned action majors, postgres service with healthcheck, seed via DATABASE_URL, uvicorn in background with a health wait that dumps the log on failure, `--with-deps chromium`, report artifact on failure, cleanup with `if: always()`); pushed to `main` (f6794da) and watched live run 29021021538 — fully green: Backend tests 1m03s, Frontend build 52s, Playwright e2e 1m43s (6 browser tests on the runner). Non-blocker: a GitHub annotation about the Node 20 deprecation inside checkout@v4/setup-python@v5 (upstream; runners force Node 24 and it works — bump action majors when new ones ship). The worker's local `--with-deps` sudo limitation is environment-only, irrelevant on hosted runners. From now on a green CI run is a mandatory acceptance condition for every task.
- 2026-07-09 · orchestrator · T12 review: accepted `[x]`, branch `feat/t12-disclaimer` fast-forward merged into `main` (a80d894) and deleted. Verified independently: branch rebased onto current main, one conventional commit, scope clean (only the sanctioned one-line FastAPI title change on the backend); brand rename complete — no "EstiHub" left in code (grep), Swagger title now "EestiHub API"; dictionaries symmetric with translated `footer`, `calculator.disclaimer`, `housing.mockNote`; `npm run build` clean; my own `npm run e2e` run → 6 passed (footer broke no locators); live spot-checks — footer with © EestiHub and the GitHub link renders on the home page, the ru calculator disclaimer and the et housing mock note render translated; footer is a Server Component mounted in the layout; EMTA/GitHub links carry `rel="noopener noreferrer"`. Pushed; the live CI run is the final gate. T11 (README + license + SEO) is now unblocked — the last task before deploy.
- 2026-07-09 · orchestrator · Record correction (owner's info): T12 was executed by **deepseek**, not gpt-5.5 — the worker column and the entry below are corrected. Quality note for future assignments: clean first-pass acceptance on a small, well-scoped frontend task; not yet evidence for complex full-stack tasks.
- 2026-07-09 · deepseek · T12 done: brand rename EstiHub→EestiHub in all frontend dictionaries and the FastAPI title; added a translated disclaimer on the calculator page with the EMTA link (`rel="noopener noreferrer"`, `target="_blank"`); added a translated mock-data note on the housing page; added `site-footer.tsx` (Server Component) with © year, disclaimer line, GitHub/EMTA links — mounted in the root layout so it appears on every page; added `footer` namespace and `calculator.disclaimer`/`housing.mockNote` keys to en/et/ru; all dictionary keys symmetric · Verified: `npm run build` passes; `npm run e2e` with backend → 6 passed (footer and disclaimer did not break any locators); `'use client'` count unchanged.
- 2026-07-09 · gpt-5.5 · T10 done: added a single GitHub Actions workflow `.github/workflows/ci.yml` for push/PR to `main` with three jobs: backend pytest on Python 3.12, frontend `npm ci` + `npm run build` on Node 22, and Playwright e2e after both jobs with a `postgres:16-alpine` service, housing seed, uvicorn backend, health wait, Chromium install and Playwright report upload on failure · Verified locally: workflow YAML parses with Python/PyYAML; backend pytest → 17 passed; frontend `npm ci` succeeds; `npm run build` passes; with compose Postgres + seed + uvicorn on `:8000`, `npm run e2e` → 6 passed. Local `npx playwright install --with-deps chromium` could not complete because sudo requires a password in this shell; plain Chromium is already installed and the e2e run passes here, while GitHub-hosted runners should allow the `--with-deps` step. No push performed; live GitHub run remains for orchestrator review.
- 2026-07-09 · orchestrator · ITERATION 4 STARTED (owner's decision: CI + disclaimer/footer + README/SEO; deploy comes after CI). ASSIGNMENTS: T10 (tasks/T10-ci.md) → gpt-5.5, in `main`, no pushing — the orchestrator pushes and verifies the live run at review; T12 (tasks/T12-disclaimer-footer.md) → gpt-5.5, branch `feat/t12-disclaimer`; T11 (tasks/T11-readme-seo.md) waits for T10+T12 (badge and footer must be on screenshots). Also per the owner's decision the repository is now public (github.com/PavluntiyJ/eestihub, default branch `main`, local `master` renamed) and ALL project documentation was translated to English by the orchestrator: CONTEXT.md, AGENTS.md, all briefs T01–T12, this board and journal (entries below are translations of the Russian originals; git history preserves the originals). English-only docs policy recorded in CONTEXT §4 and AGENTS.md. Code was already Cyrillic-free (checked; only `messages/ru.json` legitimately remains).
- 2026-07-09 · orchestrator · T09 review: accepted `[x]`, branch `feat/t09-e2e` fast-forward merged into `main` (b805770) and deleted. ITERATION 3 CLOSED. Verified independently: full `npm run e2e` run in my environment (compose Postgres + seed + uvicorn) → 6 passed in 8.6s, including the key scenario — a real calculator submit click asserting `€2,409.76` and the best badge (closes the "no browser" blind spot from the T06 review); branch rebased, one conventional commit, diff limited to e2e/config/package*/TODO, production code untouched; locators by role/label/text; chromium works in this environment. Minor nit (non-blocker): the chart check via `locator("svg").first()` is weak — replace with a data-testid or role on the next e2e change. Next: iteration 4 (CI, README/SEO, calculator disclaimer) on the owner's go; CI needs a GitHub repository.
- 2026-07-09 · gpt-5.5 · T09 done: added Playwright (`@playwright/test`) with a chromium-only config, `npm run e2e` script, an e2e smoke suite for redirect/home online, EN→ET language switch, header navigation active state, calculator submit €3000/2% asserting `€2,409.76` and the best badge, the 8-district housing table + svg chart, and disabled submit on invalid income · Verified: `npx playwright install chromium` installed a fallback chromium for this OS; `npm run build` passes; with `docker compose up -d db`, `python -m scripts.seed_housing` and uvicorn on `:8000`, `npm run e2e` → 6 passed. No production code changed; diff is only `frontend/e2e/`, `frontend/playwright.config.ts`, `frontend/package.json`, `frontend/package-lock.json` and `TODO.md`.
- 2026-07-09 · orchestrator · T08 review: accepted `[x]`. Verified independently: pytest 17 passed in my venv WITHOUT Postgres (SQLite override); live run — compose Postgres up, seed executed twice from my venv → exactly 8 rows in `district_rents` (idempotency confirmed by direct SQL), `GET /api/v1/housing/rents` → 200 with every field identical to the old mocks (checked Kesklinn and Lasnamäe by name), `updated_at: "2026-07-01"`; `docker compose stop db` → housing 503 `{"detail":"Housing rent data is unavailable"}` with no stack trace while health and calculate-taxes stay 200; frontend untouched; clean code — typed SQLAlchemy 2.x model (Mapped/mapped_column), thin route with a session dependency, the seed reused by tests, SQLite compatibility handled. Non-blocker: districts are now ordered by name (previously mock-tuple order), so the frontend table/chart order became alphabetical — the contract does not specify ordering, fine. Also re-fixed a merged journal entry (T07). Waiting for T09 (e2e) to close iteration 3.
- 2026-07-09 · gpt-5.5 · T08 done: housing rents moved to Postgres via a synchronous SQLAlchemy engine/session, added the `district_rents` model, the `python -m scripts.seed_housing` seed from `housing_data.py` with an idempotent upsert by `name`, the service reads districts from the DB ordered by `name`, `updated_at` is the max date, the route returns 503 on an unavailable/unseeded DB without a stack trace · Verified: pytest → 17 passed without Postgres (SQLite override: response shape, 8 districts, idempotent seed, 503); `docker compose up -d db` → OK; seed run twice → 8 rows; live API `/api/v1/housing/rents` → 200, 8 districts, `updated_at: "2026-07-01"`, Kesklinn/Lasnamäe values match the old mocks; `/api/v1/health` → 200 and `POST /api/v1/calculate-taxes` → 200; after `docker compose stop db` housing → 503 `{"detail": "Housing rent data is unavailable"}`, health/tax stayed 200. Frontend unchanged.
- 2026-07-09 · orchestrator · ITERATION 3 STARTED (owner's decision: Postgres + e2e; CI and README/SEO deferred to iteration 4, deploy after CI). ASSIGNMENTS: T08 → gpt-5.5 in `master`; T09 → gpt-5.5 on `feat/t09-e2e`, merge after review by the orchestrator. Task files do not overlap (backend vs frontend/e2e). Orchestrator decisions: no Alembic in the MVP (`create_all` in the seed), synchronous engine, `housing_data.py` stays the seed source, 503 on DB unavailability (the frontend already handles it); e2e — chromium only, `@playwright/test` the single new dependency, tests do not start the backend (a documented precondition), locators by role/aria. CONTEXT §2/§7 updated (Playwright, e2e/seed commands, DATABASE_URL).
- 2026-07-09 · orchestrator · T07 review: accepted `[x]`. ITERATION 2 CLOSED — the MVP is assembled (home, calculator, housing dashboard, en/et/ru, navigation). Verified independently on a prod build: en/et/ru dictionaries symmetric, the `nav` namespace translated; on `/en`, `/et/housing`, `/ru/calculator` — three translated links preserving the locale in hrefs and correct `aria-current="page"` on the active item (home matches the path exactly and is not highlighted on subpages); `site-header.tsx` stayed a Server Component, `'use client'` among the new code only in `site-nav.tsx`; responsive via flex-wrap + overflow-x-auto, no burger menu; no new dependencies; clean file scope. Accumulated tech debt for iteration 3 (from review non-blockers): x-default hreflang, `updated_at` → `date` with real housing data, the owner's manual browser pass over the calculator form, smoke commands in the README, Postgres still unused (housing on mocks). Next steps — owner's decision.
- 2026-07-09 · gpt-5.5 · T07 done: added a client `SiteNav` in the header with links to home, `/calculator` and `/housing`, active `aria-current="page"`, locale preservation via the next-intl `Link`, a responsive header layout without a burger menu; added the `nav` namespace to en/et/ru · Verified: `npm run build` passes; production `next start` smoke for `/en`, `/et/housing`, `/ru/calculator` → 200, three translated header links, hrefs preserve the locale (`/et/calculator`, `/et/housing`, etc.), the active item found by `aria-current="page"`; `'use client'` among new code only in `site-nav.tsx`; `site-header.tsx` remains a Server Component; no new dependencies.
- 2026-07-09 · orchestrator · T06 review: accepted `[x]`, branch `feat/t06-calculator-ui` fast-forward merged into `master` (8528266) and deleted. Verified independently: the branch was rebased onto current master, one conventional commit, no file-scope violations (backend, `types/api.ts`, header, housing untouched; only additions in shared files); `npm run build` clean; prod smoke `/en|et|ru/calculator` → 200 with translated h1/button; hreflang `/{locale}/calculator`; live `POST /api/v1/calculate-taxes` €3000/2% → 4 regimes, Tööleping net 2409.76; CORS preflight POST from origin :3000 → 200; dictionaries symmetric, `calculator.breakdown` covers all 5 tax_service keys, regime names come from dictionaries, the API `label` is rendered nowhere; money/percentages via `Intl.NumberFormat`; `'use client'` only in `calculator-form.tsx`; no `any`; the client form's messages are present in the flight payload (hydration gets translations); backend down → pages 200. Review limitation: the live submit click was not tested (no browser in this environment) — the code path and API/CORS were verified, risk low; the owner should run the form by eye. The Grok→gpt-5.5 worker switch due to a usage limit is recorded. ASSIGNMENT: T07 (tasks/T07-header-nav.md, new brief) → gpt-5.5, in `master`. Accepting T07 closes iteration 2.
- 2026-07-09 · gpt-5.5 · T06 done after Grok hit its limit: created the `feat/t06-calculator-ui` branch, added `calculateTaxes()` to the frontend API client, the `/[locale]/calculator` page as a Server Component with metadata/hreflang, the client tax calculator form, 4 regimes sorted by `net_income`, result cards, a Tailwind infographic, en/et/ru localization for the form, regimes, breakdown and errors · Verified: `npm run build` passes; production smoke `/en/calculator`, `/et/calculator`, `/ru/calculator` → 200 with localized form/headings; live `POST /api/v1/calculate-taxes` for €3000/2% → 4 regimes, Tööleping net 2409.76; backend down → calculator pages 200 without crashing; `'use client'` only in `calculator-form.tsx`, `rent-bar-chart.tsx` and the previously accepted `language-switcher.tsx`; the API `label` is not rendered; no `any`. No GUI/browser automation in this environment, so the submit/error UI was verified through type-check/build and the code path, without a real browser click.
- 2026-07-09 · orchestrator · T05 review: accepted `[x]`. Verified independently: pytest 15 passed in my venv; live `GET /api/v1/housing/rents` → 200, Tallinn, 8 districts, the exact §5 field set, `avg_rent_1room < avg_rent_3room` everywhere; `npm run build` clean; prod smoke `/en|et|ru/housing` → 200, translated h1/strings, all 8 districts in the table, hreflang `/{locale}/housing` correct; currency formatted per locale (en `€1,250`, ru `1 250 €`); backend down → a localized unavailable state in all three locales, no 500; `'use client'` only in `rent-bar-chart.tsx` (+ the previously accepted language-switcher); no `any`; en/et/ru dictionary keys symmetric (checked by script); file-ownership rules respected (header, tax code, others' keys untouched); recharts is the single new dependency. Architecturally flagged as a model example: the client chart receives only serializable props while the table stays a Server Component with a formatter function. Non-blocker: `updated_at` in the schema is a `str`; switch to `date` when moving to real data. Also fixed a merged T04 journal entry (an orchestrator editing mistake). Waiting for T06 (grok-4.5, branch `feat/t06-calculator-ui`); the T06 worker must rebase onto current `master`.
- 2026-07-09 · gpt-5.5 · T05 done: added the mock Housing API `GET /api/v1/housing/rents` for 8 Tallinn districts, Pydantic schemas, the service and tests; added the frontend `/[locale]/housing` with a server fetch, an unavailable state, a shadcn table, a Recharts/shadcn chart and en/et/ru i18n · Verified: pytest → 15 passed; `curl http://127.0.0.1:8000/api/v1/housing/rents` → 200 and 8 districts; `npm run build` passes; production `next start` smoke for `/en/housing`, `/et/housing`, `/ru/housing` with the backend → 200, translated strings and 8 districts; backend off → all three pages 200 with a localized unavailable state; `'use client'` only in `rent-bar-chart.tsx` and the previously accepted `language-switcher.tsx`.
- 2026-07-09 · orchestrator · ITERATION 2 STARTED (owner's decision). ASSIGNMENTS: T05 (detailed brief) → gpt-5.5-codex in `master`; T06 (new brief) → grok-4.5 (trial), branch `feat/t06-calculator-ui`, merge after review by the orchestrator. The tasks run in parallel; file-ownership zones are separated in the briefs (in shared files `lib/api.ts` and `messages/*.json` each adds only their own; nobody touches the header — navigation split into T07). Orchestrator decisions on Codex's notes: housing mock data as a separate Python module `housing_data.py` (not JSON); charts — Recharts via shadcn/ui (installed by T05, recorded in CONTEXT §2); T06 — no new dependencies, a Tailwind infographic; types from `types/api.ts` are reused, the API `label` never reaches the UI, money/percentages via `Intl.NumberFormat`; response-shape and district-count tests included in the T05 criteria.
- 2026-07-09 · orchestrator · T04 review: accepted `[x]`. Verified independently on a prod build (`npm run build` clean, `next start` + uvicorn in a clean venv): `/` → 307 `/en`; `/en`/`/et`/`/ru` → 200 with translated title/h1 and correct `lang`; hreflang en/et/ru in head; the switcher is plain `<a>` links to `/en`/`/et`/`/ru` with `aria-current`; backend up → online badge (localized in all three locales), backend killed → the page immediately shows offline without crashing (`no-store` works in prod); `types/api.ts` 1:1 with the §5 contract (snake_case, regime union); `'use client'` only in `language-switcher.tsx`; no `any`; clean working tree. Non-blockers: (1) no `x-default` in hreflang — add with the next SEO task; (2) an invalid locale `/de` → `/en/de` → 404 — standard next-intl behavior, fine; (3) no real-browser check (no GUI browser in this environment) — the interactivity is limited to plain links, minimal risk; the owner should take a look. Iteration 1 closed. Next: owner's decision on starting iteration 2 (T05 ready for assignment; T06 needs a brief).
- 2026-07-09 · gpt-5.5-codex · T04 done: added the next-intl i18n skeleton `en/et/ru`, locale routing and middleware, a typed API client, API types, a localized Server Component home page with the backend status and shadcn badge/card · Verified: `npm run build` passes; without the backend `/en` shows offline; with uvicorn `/en` shows online; `/`, `/en`, `/et`, `/ru`, `lang`, hreflang and switcher links checked via curl/HTML; `'use client'` only in `LanguageSwitcher`.
- 2026-07-09 · orchestrator · T03 re-review: accepted `[x]`. All 3 rework items done: ettevõtluskonto computes 20% + pension_pillar_rate (verified independently, including the untested 6% case → tax 780, net 2220), 0%/2% tests with derivations added, junk constants and comments removed. pytest 13 passed, the live API correct, the fix commit in place. ASSIGNMENT: T04 → gpt-5.5-codex. Reminder to the worker: the i18n skeleton is mandatory in T04 (CONTEXT.md §6); run the backend for checks from `backend/` (venv + uvicorn). Also: commit the pending orchestration-file edits (TODO.md, docs/CONTEXT.md) as `docs: update context and board after T03 review` before starting T04.
- 2026-07-09 · gpt-5.5-codex · T03 reworked per review: ettevõtluskonto now applies 20% + `pension_pillar_rate`, manual tests for 0% and 2% added/updated, redundant source comments and unused constants removed · Verified: `pytest` → 13 passed.
- 2026-07-09 · orchestrator · T03 review: REWORK (`[>]`). Verified independently: 13 tests green, the live API correct, manual tööleping/juhatuse liige/FIE derivations matched my recalculation, the 40% rate abolition and the €40,000 threshold confirmed on emta.ee. BUG FOUND: per the same EMTA page, for II pension pillar members the ettevõtluskonto rate is 20% + the contribution rate (22%/24%/26% for 2%/4%/6%); `calculate_ettevotluskonto` ignored `pension_pillar_rate` and always used 20%, overstating net for the default 0.02 input. REQUIRED: (1) apply pension_pillar_rate to the ettevõtluskonto calculation as 20% + rate, source — the same EMTA page; (2) update/add tests with manual derivations (at least the 0% and 2% cases); (3) remove meaningless source comments on trivial constants (ZERO_AMOUNT, FULL_RATE, etc.) and unused constants. CONTEXT.md §5 already updated by the orchestrator. Rework commit: `fix(backend): apply pension pillar surcharge to entrepreneur account rate`.
- 2026-07-09 · gpt-5.5-codex · T03 done: verified EMTA 2026 rates, added `tax_rates.py` with sources, Pydantic schemas, the 4-regime comparison service, a thin `POST /api/v1/calculate-taxes`, tests with manual derivations · Verified: `pytest` → 13 passed; `curl -X POST localhost:8000/api/v1/calculate-taxes` with the CONTEXT.md example → 4 results, Tööleping net 2409.76, employer_total_cost 4014.00.
- 2026-07-09 · orchestrator · T02 review: accepted `[x]`. Verified independently in a clean venv: pytest 1 passed; uvicorn starts; `GET /api/v1/health` → 200 `{"status":"ok"}`; `/docs` → 200; CORS headers for localhost:3000 correct. Code: a create_app factory, cached settings, a thin route, a Literal schema — matches the rules. Non-blocker: starlette warns about an httpx deprecation in testclient (upstream, watch on upgrades). ASSIGNMENT: T03 → gpt-5.5-codex; after handing off T03 — start T04 right away without waiting for the review (T04 does not depend on T03).
- 2026-07-09 · gpt-5.5-codex · T02 done: added FastAPI `create_app()`, a pydantic-settings config, CORS, the v1 router, `GET /api/v1/health`, a Pydantic schema and a test · Verified: `uvicorn app.main:app --reload` starts, `curl localhost:8000/api/v1/health` → `{"status": "ok"}`, `/docs` → 200 and the OpenAPI contains `/api/v1/health`, `pytest` → 1 passed.
- 2026-07-09 · orchestrator · Owner's decision: all tasks go to GPT 5.5 Codex (the DeepSeek/Grok split cancelled). T02 in progress with gpt-5.5-codex.
- 2026-07-09 · orchestrator · ASSIGNMENT: T02 → deepseek-pro-v4. The T01 dependency is closed. Additionally: include the uncommitted docker-compose.yml edit (fully qualified image name) in T02 as a separate commit `fix: use fully qualified postgres image name for podman compatibility`.
- 2026-07-09 · orchestrator · Environment: installed podman 5.8.4 + podman-compose + podman-docker (the `docker` alias works). The compose image replaced with the fully qualified `docker.io/library/postgres:16-alpine` (podman does not resolve short names). `docker compose up -d db` → container healthy, `psql` inside responds (PostgreSQL 16.14). The deferred T01 criterion is now fully closed.
- 2026-07-09 · orchestrator · T01 review: accepted `[x]`. Verified: clean git history (1 conventional commit, no artifacts/.env committed), structure per CONTEXT.md §3, compose with a healthcheck and env defaults, versions pinned, README fine. No Docker/Podman in the environment at all — the compose file passed a static check; a live Postgres run deferred until the first DB task; install docker or podman-compose before then. Next: T02 → DeepSeek Pro v4.
- 2026-07-09 · gpt-5.5 · T01 done: git init, the monorepo structure, Docker Compose for Postgres, backend requirements/env, frontend Next.js 15 + shadcn/ui, README · Verified: `npm run dev` → `GET / 200`, `pip install -r backend/requirements.txt` in a clean venv → OK, `git log` after the commit; `docker compose up -d db` not executed because `docker` is missing in the environment.
- 2026-07-09 · orchestrator · Added AGENTS.md — rules for opencode workers; model split: T01/T03 → GPT 5.5, T02 → DeepSeek Pro v4, T04 → Grok 4.5 (trial, to be adjusted by results).
- 2026-07-09 · orchestrator · Added the trilingual requirement (en/et/ru): CONTEXT.md §6, T04/T05 briefs updated.
- 2026-07-09 · orchestrator · Created the orchestration skeleton: CONTEXT.md, TODO.md, T01–T05 briefs.

## Notes for the orchestrator

_(workers write questions and out-of-scope findings here)_

- 2026-09-02 · claude-opus-5 (orchestrator) · Backlog added during wave 2.
  **Localized 404 with a correct status.** `app/` has no root layout —
  `[locale]/layout.tsx` renders `<html>` — so unmatched URLs can only reach
  Next's default 404 page. A `[...rest]` catch-all routes them into the
  localized page but returns 200 and makes the middleware advertise hreflang
  alternates for a nonexistent path; it was tried and reverted. The real fix is
  a root `app/layout.tsx` plus `app/not-found.tsx`, which touches the whole
  rendering tree and deserves its own task.
  **Dark-theme colours in the constraint list** (`CONSTRAINT_STYLES` in
  `calculator-form.tsx`) still use raw Tailwind palette classes rather than the
  design tokens. They work now that `.dark` is live, but they sit outside the
  token system; fold into whatever task next touches that component.
  **OG card title repeats the brand** — the metadata title already begins with
  "EestiHub", so the card shows the word twice. Cosmetic.

- 2026-09-02 · claude-opus-5 (orchestrator) · Audit backlog, NOT scheduled
  into iteration 7. Deferred findings: **F-12** — `/[locale]/housing`
  ships 221 kB of first-load JS against a 103 kB baseline, ~110 kB of it
  Recharts for one eight-bar chart; hand-drawn SVG in a server component
  would ship zero client JS, but that contradicts CONTEXT §2's "charts
  only via shadcn/ui chart components", so it needs a stack decision
  first. **F-18** — no ruff/mypy/pyproject on the backend; TypeScript has
  a strict gate through `next build` in CI and Python has none.
  **F-19** — the e2e smokes assert on English marketing copy and
  formatted currency, so any copy edit or rate change breaks CI for
  unrelated reasons; T17 and T20 both add assertions to that file, so
  reworking the selectors is best done once, after they land.
  Deferred features, ranked: OÜ with a salary/dividend split (22/78, 0%
  on retained profit) — the structure this audience actually uses and the
  strongest single feature available; health-insurance and pension
  eligibility per regime (the €292.38/month social tax threshold), which
  is the first real-world question these users have and which no
  competing calculator answers plainly; tax-residency switch (a
  non-resident e-resident gets no basic exemption, so the tool is most
  wrong for exactly the audience the homepage addresses); a 2025/2026
  year switcher, which A4/A5 make structural rather than cosmetic;
  prerendered `/{locale}/salary/{amount}` landing pages gated on T20's
  URL contract; JSON-LD (`WebApplication`, `Dataset`, `FAQPage`);
  per-district housing pages; a rent map using the `lat`/`lon` already in
  the schema; a tax-deadline calendar with ICS export; a move-in cost
  estimator; Lighthouse + axe gates in CI; a monthly rate-drift watchdog
  that fails when emta.ee no longer matches `tax_rates.py`; Dockerfiles
  and a one-command compose stack.

- 2026-08-23 · gpt-5.6-sol · Backlog from the owner-approved brainstorm
  (candidates for later iterations, not scheduled): real dividends-vs-
  salary OÜ comparison (extends T16); year switcher (2025/2026) + URL-
  shareable calculator scenarios; Tallinn rent heatmap map view (lat/lon
  already in the schema); Plausible/Umami privacy-friendly analytics;
  response caching to soften Render cold starts; Tartu/Pärnu districts.
  T15 deliberately scopes the data source to published aggregate stats +
  CSV (ToS-safe); an automated listing-site scraper was considered and
  rejected for now — revisit only with a licensed source.

- 2026-07-09 · gpt-5.5-codex · Codex suggestions for the orchestrator to evaluate before iteration 2 (not project rules): check T04 in a real browser beyond curl (`/`, `/en`, `/et`, `/ru`, the language switcher, `lang`, hreflang, online/offline); for T05 decide up front whether housing mock data lives in `housing_service.py` or JSON — with the current architecture a service module is simpler; add/document backend/frontend smoke commands for reviews; keep the Server Components pattern for pages in future frontend tasks with client components only for interactivity; reuse `frontend/src/types/api.ts` in T06 and do not duplicate types; do not use the backend `label` in the UI — take regime names from next-intl dictionaries; format percentages and money on the frontend without changing the API; add response-shape and district-count tests in T05; route all new visible frontend strings through `src/messages/{en,et,ru}.json`; remember that the EMTA ettevõtluskonto case proved the value of keeping tax constants only in `tax_rates.py` next to their sources.

- 2026-07-09 · gpt-5.5-codex · While verifying T03, found a discrepancy with the earlier CONTEXT.md/T03 assumption about ettevõtluskonto: the EMTA Entrepreneur account page (checked 2026-07-09) states the 40% rate no longer applies since 2025-01-01; the 2026 business income tax rate is 20% and the registration threshold is €40,000/year. The implementation uses the current EMTA 20% rate.
  - ↳ orchestrator: confirmed against the primary source, CONTEXT.md §5 updated. But the same EMTA page also has the elevated rate for II pillar members (20% + the contribution rate); that was not handled — the task was returned for rework, see the review journal entry. PARTIALLY RESOLVED.

- 2026-07-09 · gpt-5.5 · The current environment has no `docker` command, so the `docker compose up -d db` criterion and the Postgres healthcheck could not be verified locally.
  - ↳ orchestrator: confirmed, no Docker/Podman on the host — not the worker's fault. The compose file was checked statically; a live run deferred until the first DB task. RESOLVED.
