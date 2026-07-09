# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow model — this is an orchestration repo

Claude (Fable 5) acts as **Tech Lead / orchestrator only**: it designs
architecture, writes and reviews task briefs, and accepts finished work.
**It does not write application code and does not spawn agents** — code is
produced by external AI workers executing the briefs in `tasks/`.

- `docs/CONTEXT.md` — single source of truth: stack, repo structure, code
  rules, API contracts, tax logic, i18n requirements. Workers must read it
  before any task; only the orchestrator edits it.
- `TODO.md` — task board (statuses `[ ]`/`[>]`/`[R]`/`[x]`), journal
  (newest first), and a "notes for orchestrator" section where workers
  report out-of-scope findings. Only the orchestrator sets `[x]`.
- `tasks/T##-*.md` — self-contained briefs: goal, steps, explicit
  non-goals, acceptance criteria. Orchestrator writes them; workers execute
  and flip the task to `[R]` for review.
- All project documentation (docs, briefs, TODO board and journal) is
  written in English — the repo is public and goes into a portfolio.
  Conversation with the owner stays in Russian.

When resuming a session: read `TODO.md` first, then review any `[R]` tasks
against their acceptance criteria and `docs/CONTEXT.md` before accepting.

## Project

EestiHub — web service for expats/entrepreneurs in Estonia. MVP: Estonian
tax-regime comparison calculator and a Tallinn rent-prices dashboard.
Trilingual (en default / et / ru) via next-intl. Portfolio project — clean
architecture matters.

Stack: Next.js 15 (App Router, TS strict, Tailwind, shadcn/ui) in
`frontend/`; FastAPI + Pydantic v2 + SQLAlchemy in `backend/`;
PostgreSQL 16 via `docker-compose.yml`.

Key invariants (details in `docs/CONTEXT.md`):
- Tax rates live only in `backend/app/core/tax_rates.py`, with sources.
- FastAPI routes are thin; math lives in `backend/app/services/`.
- Frontend `src/types/` mirrors backend Pydantic schemas 1:1 (snake_case).
- Server Components by default; `'use client'` only for interactivity.
- No `any`; no hardcoded UI strings (next-intl dictionaries in `src/messages/`).
- API is locale-neutral (machine keys); UI labels come from dictionaries.

## Commands (once T01/T02 are done)

```bash
docker compose up -d db                      # Postgres :5432
cd backend && uvicorn app.main:app --reload  # API :8000, Swagger at /docs
cd backend && pytest                         # backend tests
cd frontend && npm run dev                   # UI :3000
cd frontend && npm run build                 # type/lint gate
```
