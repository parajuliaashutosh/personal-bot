from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api import chat_routes, ingest_routes
from app.middleware.apikey_middleware import apikey_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.logging_middleware import logging_middleware
from shared.config.settings import settings
from shared.db.postgres import close_pool, get_pool, run_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    await run_migrations()

    # Embed: gemini preferred (if key present), else ollama
    if settings.gemini_api_key:
        from retrieval.llm.gemini import embed
    else:
        from retrieval.llm.ollama import embed  # type: ignore[no-redef]

    # Build generate chain: primary → github_models → gemini (each skipped if key absent)
    from retrieval.llm.fallback import with_fallback

    _providers = []
    if settings.llm_provider == "openrouter" and settings.openrouter_api_key:
        from retrieval.llm.openrouter import generate as _g
        _providers.append(_g)
    if settings.github_models_token:
        from retrieval.llm.github_models import generate as _gh  # type: ignore[no-redef]
        _providers.append(_gh)
    if settings.gemini_api_key:
        from retrieval.llm.gemini import generate as _gm  # type: ignore[no-redef]
        _providers.append(_gm)
    if not _providers or settings.llm_provider == "ollama":
        from retrieval.llm.ollama import generate as _ol  # type: ignore[no-redef]
        _providers.append(_ol)

    generate = _providers[-1]
    for _p in reversed(_providers[:-1]):
        generate = with_fallback(_p, generate)  # type: ignore[assignment]

    row = await pool.fetchrow("SELECT raw_text FROM persona WHERE id = 1")
    app.state.persona_text = row["raw_text"] if row else ""

    app.state.pool = pool
    app.state.generate_fn = generate
    app.state.embed_fn = embed

    yield

    await close_pool()


app = FastAPI(title="Personal RAG API", lifespan=lifespan)

# Middleware — last registered = outermost (first to handle requests)
app.middleware("http")(error_middleware)
app.middleware("http")(logging_middleware)
app.middleware("http")(apikey_middleware)

# CORS must be registered last so it becomes outermost and handles preflight before any other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization", "Accept"],
)

app.include_router(ingest_routes.router)
app.include_router(chat_routes.router)


@app.get("/health", tags=["health"])
async def health(request: Request):
    try:
        pool = request.app.state.pool
        await pool.fetchval("SELECT 1")
        return {"status": "ok", "db": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": str(exc)},
        )


def _custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "ApiKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Chat routes: use API_KEY. Ingest/admin routes: use ADMIN_KEY.",
        }
    }
    schema["security"] = [{"ApiKeyHeader": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[method-assign]
