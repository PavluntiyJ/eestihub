# DEPLOY.md — EestiHub production deploy runbook

This runbook deploys EestiHub to three free-tier services. Follow the steps
in order. Every step is a dashboard action — no CLI or code changes needed.

## Prerequisites

- A GitHub account with access to the `PavluntiyJ/eestihub` repository.
- Accounts on [Neon](https://neon.tech), [Render](https://render.com)
  and [Vercel](https://vercel.com). Sign up with GitHub for the
  simplest integration.

---

## 1. Neon — managed PostgreSQL

1. Log into [Neon](https://console.neon.tech) → **New Project**.
2. Name it `eestihub`, choose the **Free** plan, region closest to you
   (Frankfurt if available).
3. Once created, open the **Dashboard** and copy the connection string.
   It looks like:
   ```
   postgresql://neondb_owner:npg_xxxxx@ep-xxxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Adapt it for SQLAlchemy/psycopg**: replace the scheme with
   `postgresql+psycopg://` and keep `?sslmode=require`. Example:
   ```
   postgresql+psycopg://neondb_owner:npg_xxxxx@ep-xxxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
5. Save this string — you will paste it into Render in step 2.

---

## 2. Render — backend

The repository already contains a `render.yaml` Blueprint at the root.
Render reads it automatically.

1. Log into [Render](https://dashboard.render.com) → **New** →
   **Blueprint**.
2. Connect your GitHub account, select the `PavluntiyJ/eestihub`
   repository. Render picks up `render.yaml`.
3. Before clicking **Apply**, set the two environment variables that
   are declared with `sync: false` (meaning they are **not** in the file
   and must be provided here):
   - `DATABASE_URL` — the adapted Neon connection string from step 1.
   - `CORS_ORIGINS` — the Vercel URL you will get in step 3, with no
     trailing slash. You can set this to a placeholder (e.g.
     `https://eestihub.vercel.app`) now and update it after Vercel
     deploys.
4. Click **Apply**. Render builds the backend, seeds the database
   (the seed is idempotent — safe to run every boot), and starts the
   API.
5. Wait for the deploy to finish, then note the **`onrender.com` URL**
   (something like `https://eestihub-api.onrender.com`).
6. Verify: open `https://<your-url>.onrender.com/api/v1/health` in a
   browser — you should see `{"status":"ok"}`.

---

## 3. Vercel — frontend

1. Log into [Vercel](https://vercel.com) → **Add New** → **Project**.
2. Import the `PavluntiyJ/eestihub` repository.
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js (Vercel detects it automatically)
4. Set **Environment Variables**:
   - `NEXT_PUBLIC_API_URL` — the Render URL from step 2
     (e.g. `https://eestihub-api.onrender.com`).
   - `NEXT_PUBLIC_SITE_URL` — the Vercel domain you will get after
     deploy (Vercel auto-generates one like
     `https://eestihub.vercel.app`). You can estimate it and update
     after deploy.
5. Click **Deploy**.
6. Once built, note the Vercel domain (e.g.
   `https://eestihub.vercel.app`).

---

## 4. Update CORS_ORIGINS on Render

Now that you have the real Vercel domain, update CORS on the backend:

1. Go to your **Render Dashboard** → the `eestihub-api` service →
   **Environment** tab.
2. Edit `CORS_ORIGINS` to your Vercel domain **without a trailing
   slash**:
   ```
   https://eestihub.vercel.app
   ```
3. Render redeploys automatically after an env var change. Wait for
   the deploy to finish.

---

## 5. GitHub — keep-alive variable

The backend on Render Free spins down after 15 minutes of inactivity.
A GitHub Actions workflow (already in the repo) pings the health
endpoint every 10 minutes to prevent this.

1. Go to your GitHub repository → **Settings** → **Secrets and
   variables** → **Actions** → **Variables** tab.
2. Click **New repository variable**:
   - Name: `BACKEND_URL`
   - Value: your **Render URL**, without a trailing slash
     (e.g. `https://eestihub-api.onrender.com`)
3. The workflow `keepalive.yml` starts running on the next cron tick.
   Until the variable is set it skips gracefully (green).

---

## 6. Smoke checks

| Check | What to do | Expected result |
|---|---|---|
| Backend health | Open `<render-url>/api/v1/health` | `{"status":"ok"}` |
| Calculator | Visit the Vercel URL, go to **Calculator**, submit with €3000/2% | 4 regimes, best badge, `€2,409.76` net for Tööleping |
| Housing dashboard | Go to **Rent** | Table with 8 Tallinn districts, bar chart, "Updated 2026-07-01" |
| i18n | Switch language to ET, then RU | Every string translated, URLs are `/et/...` and `/ru/...` |
| Sitemap | Open `<vercel-url>/sitemap.xml` | 9 `<url>` entries (3 pages × 3 locales) with alternates |
| Keep-alive | GitHub Actions tab → Keep-alive workflow → latest run | Green; log shows `{"status":"ok"}` from Render |

If the backend shows a cold start (~30–60 s on first request after a
pause), wait a moment and retry. The keep-alive cron prevents this for
subsequent visitors.

---

## Free-tier caveats

- **Render Free** spins down the backend after 15 minutes of no
  inbound traffic. The GitHub keep-alive cron pings every 10 minutes to
  keep it warm. The first request after a missed interval may take
  ~1 minute (cold start).
- **Neon Free** scales compute to zero after inactivity. The
  database resumes in under a second on the next query, but the
  very first connection after a long idle period can time out once —
  the API returns 503 for housing and the frontend shows an unavailable
  state. A page refresh resolves it.
- **GitHub Actions** disables scheduled workflows after 60 days of
  repository inactivity. Pushing any commit or running the workflow
  manually (from the Actions tab) resets the counter.
- **Neon Free** has a 0.5 GiB storage limit and a 100-hour monthly
  compute limit — more than enough for a portfolio project.
