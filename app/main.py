from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import chat_routes, ingest_routes
from app.limiter import limiter
from app.middleware.apikey_middleware import apikey_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.logging_middleware import logging_middleware
from shared.config.settings import settings
from shared.db.postgres import close_pool, get_pool, run_migrations

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


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
        # type: ignore[no-redef]
        from retrieval.llm.github_models import generate as _gh
        _providers.append(_gh)
    if settings.gemini_api_key:
        # type: ignore[no-redef]
        from retrieval.llm.gemini import generate as _gm
        _providers.append(_gm)
    if not _providers or settings.llm_provider == "ollama":
        # type: ignore[no-redef]
        from retrieval.llm.ollama import generate as _ol
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

    # Close shared HTTP clients
    from retrieval.llm.openrouter import _client as _or_client
    from retrieval.llm.github_models import _client as _gh_client
    from retrieval.llm.ollama import _client as _ol_client, _embed_client as _ol_embed_client
    from retrieval.memory.session import _geo_client
    for _c in (_or_client, _gh_client, _ol_client, _ol_embed_client, _geo_client):
        await _c.aclose()


app = FastAPI(title="Personal RAG API",
              lifespan=lifespan, redirect_slashes=False)


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"success": False, "code": "RATE_LIMITED",
                 "message": "Too many requests. Slow down."},
    )


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# Middleware — last registered = outermost (first to handle requests)
app.add_middleware(SlowAPIMiddleware)
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


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
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
    schema = get_openapi(
        title=app.title, version=app.version, routes=app.routes)
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
