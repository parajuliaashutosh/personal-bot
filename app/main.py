from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi.middleware import SlowAPIMiddleware

from app.api import admin_routes, auth_routes, chat_routes, ingest_routes
from app import responses
from app.limiter import limiter
from app.middleware.apikey_middleware import apikey_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.logging_middleware import logging_middleware
from app.middleware.path_middleware import trailing_slash_middleware
from shared.config.settings import settings
from shared.db.postgres import close_pool, get_pool, run_migrations, seed_admin_user

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be set to at least 32 characters")
    pool = await get_pool()
    await run_migrations()
    await seed_admin_user(pool)

    from retrieval.llm.embeddings import embed


    from retrieval.llm.fallback import with_fallback, with_retry
    from retrieval.llm.guards import with_idle_timeout

    _providers: list[tuple[str, object]] = []
    if settings.openrouter_api_key:
        from retrieval.llm.openrouter import generate as _or
        _providers.append(("openrouter", _or))
    if settings.anthropic_api_key:
        from retrieval.llm.anthropic import generate as _an
        _providers.append(("anthropic", _an))
    if not _providers:
        raise RuntimeError(
            "No LLM provider configured: set OPENROUTER_API_KEY and/or ANTHROPIC_API_KEY")
    _providers.sort(key=lambda p: p[0] != settings.llm_provider)

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
    from retrieval.llm.anthropic import _client as _an_client
    from retrieval.llm.embeddings import _client as _emb_client
    from retrieval.llm.openrouter import _client as _or_client
    from retrieval.memory.session import _geo_client
    for _c in (_or_client, _an_client, _emb_client, _geo_client):
        await _c.aclose()


app = FastAPI(title="Personal RAG API",
              lifespan=lifespan, redirect_slashes=False)


app.state.limiter = limiter
responses.install(app)

# Middleware — last registered = outermost (first to handle requests)
app.add_middleware(SlowAPIMiddleware)
app.middleware("http")(logging_middleware)
app.middleware("http")(apikey_middleware)
app.middleware("http")(trailing_slash_middleware)
# Outside apikey_middleware so its 401/403 responses are recorded too.
app.middleware("http")(error_middleware)

# CORS must be registered last so it becomes outermost and handles preflight before any other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key",
                   "X-SESSION-ID", "X-Retry-Attempt", "Authorization", "Accept"],
)

app.include_router(ingest_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)
app.include_router(auth_routes.router)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
async def health(request: Request):
    try:
        pool = request.app.state.pool
        await pool.fetchval("SELECT 1")
        return responses.ok({"status": "ok", "db": "ok"})
    except Exception as exc:
        return responses.fail(503, "SERVICE_DEGRADED", "Database unreachable",
                              {"status": "degraded", "db": str(exc)}, request=request)


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
            "description": "Chat routes: use API_KEY. Ingest/admin routes: log in and send the JWT as a Bearer token.",
        }
    }
    schema["security"] = [{"ApiKeyHeader": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[method-assign]
