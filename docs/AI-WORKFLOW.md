# AI-orchestrated development workflow

EestiHub is not only a full-stack application; it is also a case study in
running a real project with coding agents under human direction. This
document describes the workflow that produced every commit in this
repository, so the history can be read as evidence rather than as a claim.

## Roles

| Role | Who | Responsibility |
|---|---|---|
| Owner | Human | Sets direction, approves iterations, reviews the result |
| Orchestrator | Claude (one long-lived agent) | Architecture, `docs/CONTEXT.md`, task briefs, reviews, accept/reject |
| Workers | GPT-5.5, GPT-5.5 Codex, gpt-5.6-sol, gpt-5-codex, DeepSeek, DeepSeek Pro v4, claude-opus-5, opencode | Execute exactly one brief, run the acceptance checks, hand off |

The orchestrator never writes application code (with two documented
exceptions where the worker ran out of budget; the journal marks those
acceptances as lacking independent review). Workers never review their own
work, and never set a task to `[x]` — only the orchestrator accepts.

The portfolio-hardening pass (workstreams H1–H4: accessibility gates,
Lighthouse CI, Docker, this document) was owner-directed and had no task
briefs; its review record lives in `TODO.md`.

## Artifacts

- **`docs/CONTEXT.md`** — the single source of truth: stack, repo layout,
  code rules, API contract, tax logic with sources, i18n requirements.
  Every worker reads it in full before touching code. Only the orchestrator
  edits it.
- **`tasks/T##-*.md`** — self-contained briefs: goal, numbered steps,
  explicit non-goals, acceptance criteria, and two binding extra sections:
  - **Files you own** — parallel tasks never share a write zone; overlaps
    are resolved when briefs are written, not at merge time.
  - **Documentation impact** — the statements this task will falsify,
    named file by file. A task is not done if the README still describes
    the old behaviour.
- **`TODO.md`** — the task board (`[ ]` → `[>]` → `[R]` → `[x]`) plus a
  journal in which every worker records what was done and how it was
  verified, and where the orchestrator records the review verdict.
- **`AGENTS.md` / `CLAUDE.md`** — the worker and orchestrator contracts.

## The loop

1. The owner picks a direction; the orchestrator turns it into briefs with
   acceptance criteria and a dependency order.
2. Workers set their task to `[>]`, implement it on a branch or `main`,
   run every acceptance check, update `TODO.md`, and set it to `[R]`.
3. The orchestrator verifies independently — it does not trust the worker's
   summary. Verification includes re-running the suite, reading the diff
   against the brief's scope, and re-checking domain constants against
   primary sources.
4. Accepted → `[x]` and a journal entry. Rejected → a "Rework" section is
   appended to the same brief and the task returns to `[>]`.

## What the process actually caught

- **A wrong tax rate in the spec itself.** The II pension pillar rule for
  management-board members in `CONTEXT.md` was incorrect, and the code
  implemented it as written. The audit caught it against the EMTA primary
  source (finding F-01); the spec was corrected before the remediation
  briefs (T17) were written.
- **A calculation bug returned for rework.** T03's entrepreneur-account
  rate ignored the pension pillar surcharge; the orchestrator refused the
  hand-off and requested tests with hand derivations.
- **A rendering bug found by review.** Negative FIE net income produced an
  invalid CSS width that rendered the worst regime as a full bar (T17
  rework round 1).
- **Documentation rot, twice.** A worker shipped sourced rent data while
  the README still called it demo data, and iteration 7's user-facing
  features went unmentioned. The fix was structural: `tasks/TEMPLATE.md`
  now makes **Documentation impact** a mandatory brief section.
- **Real user-visible accessibility and SEO defects.** The axe and
  Lighthouse gates added in the portfolio-hardening pass found
  `role="status"` on `<main>` in the loading skeleton, and canonical,
  hreflang and meta description stranded in `<body>` on the dynamic routes
  (fixed with blocking metadata).
- **A CI race, not an app bug.** An e2e failure was traced to Playwright
  driving inputs before React hydrated; the fix was retrying helpers, and
  the journal entry records the misdiagnosis that preceded it. A later,
  similar-looking failure in the URL-writing test turned out to be an
  app-side router race instead; the journal records that diagnosis too.

## Quality gates

A task cannot be accepted unless all of these pass:

- `pytest` in `backend/` (55 tests, including a 20-row golden-file suite
  with hand-derived net incomes);
- `npm run build` in `frontend/` (TypeScript strict is the type gate);
- `npm run e2e` (Playwright: 15 product smokes + 8 axe accessibility scans);
- Lighthouse CI assertions: accessibility and SEO at 100, best-practices
  at 95+, performance as a warning;
- `docker compose build && docker compose up` smoke (the whole stack boots,
  seeds Postgres and serves data through the container network);
- a green GitHub Actions run on `main`.

## Why this matters for an AI-first team

The hard part of agentic development is not generation, it is context and
verification. This repository shows the practices that worked here:

- one authoritative context document instead of repeated prompt folklore;
- small briefs with explicit non-goals, so scope creep is visible in a diff;
- file ownership declared up front, so parallel agents do not collide;
- machine-checkable acceptance criteria, re-run by the reviewer;
- verification against primary sources (emta.ee, e-Residency knowledge base)
  rather than against the model's memory;
- a written journal that records rejected work and mistakes, not only wins.
