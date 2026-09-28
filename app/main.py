from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import admin_routes, chat_routes, ingest_routes
from app.limiter import limiter
from app.middleware.apikey_middleware import apikey_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.logging_middleware import logging_middleware
from app.middleware.path_middleware import trailing_slash_middleware
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
    # Each provider is wrapped as: idle-timeout → retry → fallback to the next.
    from retrieval.llm.fallback import with_fallback, with_retry
    from retrieval.llm.guards import with_idle_timeout

    _providers: list[tuple[str, object]] = []
    if settings.llm_provider == "openrouter" and settings.openrouter_api_key:
        from retrieval.llm.openrouter import generate as _g
        _providers.append(("openrouter", _g))
    if settings.github_models_token:
        # type: ignore[no-redef]
        from retrieval.llm.github_models import generate as _gh
        _providers.append(("github_models", _gh))
    if settings.gemini_api_key:
        # type: ignore[no-redef]
        from retrieval.llm.gemini import generate as _gm
        _providers.append(("gemini", _gm))
    if not _providers or settings.llm_provider == "ollama":
        # type: ignore[no-redef]
        from retrieval.llm.ollama import generate as _ol
        _providers.append(("ollama", _ol))

    def _harden(name: str, fn):
        fn._provider_name = name  # type: ignore[attr-defined]
        return with_retry(with_idle_timeout(fn))

    _hardened = [_harden(name, fn) for name, fn in _providers]

    generate = _hardened[-1]
    for _p in reversed(_hardened[:-1]):
        generate = with_fallback(_p, generate)  # type: ignore[assignment]

    logging.getLogger(__name__).info(
        "LLM chain: %s (retries=%d, idle_timeout=%.0fs, continue_on_truncation=%s)",
        " -> ".join(name for name, _ in _providers),
        settings.llm_retry_attempts,
        settings.llm_stream_idle_timeout,
        settings.llm_continue_on_truncation,
    )

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
app.middleware("http")(trailing_slash_middleware)

# CORS must be registered last so it becomes outermost and handles preflight before any other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key",
                   "X-SESSION-ID", "Authorization", "Accept"],
)

app.include_router(ingest_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)


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
