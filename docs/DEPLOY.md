# DEPLOY.md — EestiHub production deploy runbook

This runbook deploys EestiHub to Vercel, Render and Neon. Existing accounts
and services are reused for the September planner release; no paid upgrade
is required. Initial setup is described below; transit data also needs the
maintenance CLI described in section 6.

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
   browser — you should see `{"status":"ok","database":"ok"}`.

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

## 5. Smoke checks

| Check | What to do | Expected result |
|---|---|---|
| Backend health | Open `<render-url>/api/v1/health` | `{"status":"ok","database":"ok"}` |
| Calculator | Visit the Vercel URL, go to **Calculator**, submit with €3000/2% | 4 regimes, best badge, `€2,409.76` net for Tööleping |
| Housing dashboard | Go to **Rent** | Table with 8 Tallinn districts, bar chart and actual snapshot date |
| i18n | Switch language to ET, then RU | Every string translated, URLs are `/et/...` and `/ru/...` |
| Sitemap | Open `<vercel-url>/sitemap.xml` | 15 `<url>` entries (5 pages × 3 locales) with alternates |
| Apartment planner | Enter net 2400, spending 700, savings 300, share 35%, rent 650, utilities 100/200 | Allowance 840; seasonal totals 750/850 and remainder 650/550 |
| Address and transport | Select Mustamäe tee 5, open map | Real nearby platforms, service date and source credit, matching map markers |

If the backend shows a cold start (~30–60 s on first request after a
pause), wait a moment and retry.

---

## 6. Transit data for the planner

After the backend release is available, run from `backend/` with the production
Neon `DATABASE_URL` supplied through the environment (never paste credentials
into commands committed to Git):

```bash
python -m scripts.import_gtfs
```

This creates missing transit tables additively, validates the official Tallinn
feed and atomically activates a snapshot. It does not modify housing or user
data. Confirm `/api/v1/transit/nearby?lat=59.426593&lon=24.7034` returns 200,
nonempty `stops`, source dates and license attribution. A 503 before this first
import is expected. Refresh through the same CLI; the previous snapshot survives
a failed refresh. No download is added to API boot or request handling.

Refresh is currently an operator action; a daily run is suggested but no
schedule is installed by this release. After seven days without a successful
check, the frontend warns that the snapshot is stale. See
[TRANSIT-OPERATIONS.md](TRANSIT-OPERATIONS.md) for the full freshness policy,
failure recovery and exit codes.

## Free-tier caveats

- **Render Free** spins down the backend after 15 minutes of no
  inbound traffic. The first request after a pause takes ~1 minute
  (cold start) while the service wakes up.
- **Neon Free** scales compute to zero after inactivity. The
  database resumes on the next query. The API validates pooled
  connections before use and replaces stale ones automatically. The
  health endpoint returns 503 with `database: "unavailable"` if Neon
  cannot be reached, while tax calculations remain available because
  they do not depend on the database.
- **Neon Free** has a 0.5 GiB storage limit and a 100-hour monthly
  compute limit — more than enough for a portfolio project.
