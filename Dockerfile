# ── build stage ───────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Install deps first (cached layer), then install project
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ app/
COPY ingestion/ ingestion/
COPY retrieval/ retrieval/
COPY shared/ shared/
RUN uv sync --frozen --no-dev

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" --uid 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app app/
COPY --from=builder /app/ingestion ingestion/
COPY --from=builder /app/retrieval retrieval/
COPY --from=builder /app/shared shared/
COPY pdfs/ pdfs/

ENV PATH="/app/.venv/bin:$PATH" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
