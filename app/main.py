from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import ingest_routes
from app.middleware.apikey_middleware import apikey_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.logging_middleware import logging_middleware
from shared.config.settings import settings
from shared.db.postgres import close_pool, get_pool, run_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ────────────────────────────────────────────────────────────────
    pool = await get_pool()
    await run_migrations()

    # Wire LLM provider
    if settings.llm_provider == "gemini":
        from retrieval.llm.gemini import embed, generate
    else:
        from retrieval.llm.ollama import embed, generate  # type: ignore[no-redef]

    app.state.pool = pool
    app.state.generate_fn = generate
    app.state.embed_fn = embed

    yield

    # ── shutdown ───────────────────────────────────────────────────────────────
    await close_pool()


app = FastAPI(title="Personal RAG API", lifespan=lifespan)

# Middleware — last registered = outermost (first to handle requests)
app.middleware("http")(error_middleware)
app.middleware("http")(logging_middleware)
app.middleware("http")(apikey_middleware)

app.include_router(ingest_routes.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
