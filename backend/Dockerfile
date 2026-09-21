# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

USER app

EXPOSE 8000

# The seed and ingest commands are idempotent, so booting through them is safe
# on every start; compose waits for Postgres to be healthy before this runs.
CMD ["sh", "-c", "python -m scripts.seed_housing && python -m scripts.ingest_rents && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
