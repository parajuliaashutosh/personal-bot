from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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

    if settings.llm_provider == "gemini":
        from retrieval.llm.gemini import embed, generate
    else:
        from retrieval.llm.ollama import embed, generate  # type: ignore[no-redef]

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
