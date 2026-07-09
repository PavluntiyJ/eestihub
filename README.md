# EstiHub

EstiHub is an interactive web service for expats and entrepreneurs in Estonia. The MVP will include a tax comparison calculator and a Tallinn rental housing dashboard.

## Stack

- Frontend: Next.js 15 App Router, TypeScript strict, Tailwind CSS, shadcn/ui
- Backend: FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.x
- Database: PostgreSQL 16 via Docker Compose

## Local Development

Start PostgreSQL:

```bash
docker compose up -d db
```

Start the backend after T02 adds the FastAPI app:

```bash
cd backend
uvicorn app.main:app --reload
```

Start the frontend:

```bash
cd frontend
npm run dev
```

PostgreSQL runs on `localhost:5432`. The frontend uses `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.
