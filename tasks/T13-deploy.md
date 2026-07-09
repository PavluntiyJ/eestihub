# T13 — Deploy config: Render blueprint, keep-alive, deploy runbook

**Read first:** `docs/CONTEXT.md` (§1–§3, §7).
**Dependencies:** T11 accepted. **Role:** DevOps/Docs.
**Branch:** work in `main`.

## Context

The project deploys to free tiers: frontend → Vercel Hobby, backend →
Render Free (spins down after 15 min idle), Postgres → Neon Free.
Accounts exist. All dashboard clicking is done by the owner following a
runbook you write; your job is only the repo-side files. The backend is
already fully env-driven (`DATABASE_URL`, `CORS_ORIGINS` — see
`backend/app/core/config.py`); do not change application code.

## Steps

1. **`render.yaml`** (repo root) — a Render Blueprint with one web
   service:
   - `env: python`, `rootDir: backend`, `plan: free`,
     `region: frankfurt`;
   - build: `pip install -r requirements.txt`;
   - start: `python -m scripts.seed_housing && uvicorn app.main:app
     --host 0.0.0.0 --port $PORT` (the seed is idempotent — safe on
     every boot);
   - env vars: `PYTHON_VERSION=3.12` (value in the file), and
     `DATABASE_URL`, `CORS_ORIGINS` declared with `sync: false` (set in
     the dashboard, never committed);
   - health check path `/api/v1/health`.
2. **Keep-alive workflow** `.github/workflows/keepalive.yml`:
   - `schedule` cron every 10 minutes + `workflow_dispatch`;
   - one job, one step: `curl --fail --max-time 30` to
     `${{ vars.BACKEND_URL }}/api/v1/health`; skip gracefully (exit 0
     with a notice) when `vars.BACKEND_URL` is not set, so the workflow
     is green before the first deploy;
   - do not touch the existing `ci.yml`.
3. **`docs/DEPLOY.md`** — a step-by-step English runbook for the owner:
   - Neon: create a project, copy the connection string, adapt it to
     the SQLAlchemy scheme `postgresql+psycopg://...` (keep
     `sslmode=require`);
   - Render: New → Blueprint from the GitHub repo, set `DATABASE_URL`
     and `CORS_ORIGINS` (the Vercel URL, no trailing slash) in the
     dashboard; note the `onrender.com` URL;
   - Vercel: import the repo, root directory `frontend`, framework
     Next.js; env vars `NEXT_PUBLIC_API_URL` (the Render URL) and
     `NEXT_PUBLIC_SITE_URL` (the Vercel URL);
   - GitHub: create the repository variable `BACKEND_URL` (Settings →
     Secrets and variables → Actions → Variables) for the keep-alive;
   - order of operations (Neon → Render → Vercel → CORS_ORIGINS update →
     BACKEND_URL) and a smoke-check list (health endpoint, calculator
     submit, housing table, `/sitemap.xml` with the prod domain);
   - a "Free-tier caveats" note: Render cold start ~1 min, Neon
     scale-to-zero, GitHub disables cron workflows after 60 days of repo
     inactivity.
4. **README**: add a short "Deployment" section linking to
   `docs/DEPLOY.md` (one paragraph: Vercel + Render + Neon free tiers,
   see the runbook). Leave a `<!-- TODO: live demo URL -->` comment at
   the top of the README where the live link will go — the orchestrator
   adds the real URL after the owner deploys.

## Non-goals

- No application-code changes (backend or frontend `src/`).
- No changes to `ci.yml`, the e2e suite, or docker-compose.
- No dashboard actions — the owner executes the runbook.
- No custom domain, analytics, or monitoring beyond the keep-alive.

## Acceptance criteria

- [ ] `render.yaml` is a valid Blueprint (YAML parses; fields per
      current Render docs), seeds idempotently on boot, no secrets
      committed.
- [ ] `keepalive.yml` parses, is green when `BACKEND_URL` is unset, and
      does not modify `ci.yml`.
- [ ] `docs/DEPLOY.md` is complete enough that a person who has never
      used these dashboards can deploy by following it top to bottom.
- [ ] README has the Deployment section and the live-URL placeholder.
- [ ] `git diff` touches only: `render.yaml`,
      `.github/workflows/keepalive.yml`, `docs/DEPLOY.md`, `README.md`,
      `TODO.md`.

## Verification

- YAML of both new files parses (e.g. `python -c "import yaml, sys;
  yaml.safe_load(open('render.yaml'))"`).
- `cd frontend && npm run build` still passes (nothing should have
  changed — this is a regression guard).
- Commit: `ci: render blueprint, keep-alive ping and deploy runbook`.

## On completion

Set T13 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
