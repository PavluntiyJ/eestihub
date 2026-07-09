# T01 — Monorepo scaffold

**Read first:** `docs/CONTEXT.md` (sections 2, 3, 6).
**Dependencies:** none. **Role:** DevOps / Fullstack.

## Goal
Turn the empty project folder into a working monorepo skeleton: git,
folder structure, Docker Compose with Postgres, base frontend/backend
configs.

## Steps

1. `git init`, create `.gitignore` (Python + Node + Next.js + .env + IDE).
2. Create the folder tree exactly per CONTEXT.md section 3 (empty Python
   packages get `__init__.py`).
3. `docker-compose.yml` at the root: `db` service — `postgres:16-alpine`,
   port 5432, data volume, healthcheck, credentials via env
   (defaults: estihub/estihub/estihub_dev).
4. `backend/requirements.txt`: fastapi, uvicorn[standard], pydantic>=2,
   pydantic-settings, sqlalchemy>=2, psycopg[binary], pytest, httpx.
   Pin versions to current stable releases.
5. `backend/.env.example`: DATABASE_URL, CORS_ORIGINS.
6. Frontend: `npx create-next-app@latest frontend` — TypeScript,
   Tailwind, App Router, `src/` directory, ESLint. Then initialize
   shadcn/ui (`npx shadcn@latest init`). Add `frontend/.env.example`
   with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
7. Root `README.md` (English, brief): what the project is, stack, how to
   run it (CONTEXT.md section 7).
8. Commit: `chore: scaffold monorepo (frontend, backend, docker-compose)`.

## Non-goals
- No endpoints or business logic (that's T02/T03).
- No backend/frontend services in docker-compose (db only for now).
- No extra "just in case" dependencies.

## Acceptance criteria
- [ ] `docker compose up -d db` starts Postgres, healthcheck green.
- [ ] `cd frontend && npm run dev` serves the default page without errors.
- [ ] `pip install -r backend/requirements.txt` succeeds in a clean venv
      (Python 3.11+).
- [ ] `git log` has one meaningful commit; `.env` files are gitignored.

## On completion
Set T01 to `[R]` in `TODO.md` and add a journal entry
(date · who · what was done · how it was verified).
