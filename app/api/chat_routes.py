from __future__ import annotations

import json
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.limiter import limiter
from retrieval.memory.chat_history import save_message
from retrieval.memory.session import (
    create_session,
    enrich_session_geo,
    get_session,
    update_last_active,
    validate_session_id,
)
from retrieval.services.chat_service import build_chat_pipeline
from shared.config.settings import settings
from shared.models.schema import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def _extract_ip(request: Request) -> tuple[str | None, str | None]:
    """Return (real_ip, raw_x_forwarded_for). Prefers CF-Connecting-IP, then XFF, then client.host."""
    xff = request.headers.get("X-Forwarded-For")
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip(), xff
    if xff:
        return xff.split(",")[0].strip(), xff
    fallback = request.client.host if request.client else None
    return fallback, None


@router.post("/session", status_code=201)
async def create_chat_session(
    request: Request,
    background_tasks: BackgroundTasks,
):
    pool = request.app.state.pool
    ip, xff = _extract_ip(request)
    user_agent = request.headers.get("user-agent")

    session_id = await create_session(ip, user_agent, pool, xff)

    if ip and settings.ipinfo_api_key:
        background_tasks.add_task(
            enrich_session_geo, str(session_id), ip, pool)

    response = JSONResponse(
        status_code=201,
        content={"success": True, "message": "session created",
                 "data": {"session_id": str(session_id)}},
    )
    response.headers["X-Session-Id"] = str(session_id)
    return response


@router.post("/")
@limiter.limit("2/minute")
async def chat(body: ChatRequest, request: Request):
    from shared.security.sanitizer import sanitize_query

    pool = request.app.state.pool
    generate_fn = request.app.state.generate_fn
    embed_fn = request.app.state.embed_fn

    # ── Session resolution ────────────────────────────────────────────────────
    raw_session_id = request.headers.get("X-Session-Id")

    if raw_session_id:
        if not validate_session_id(raw_session_id):
            raise HTTPException(
                status_code=400,
                detail={"code": "SESSION_INVALID_ID",
                        "message": "Invalid session ID format"},
            )
        session = await get_session(raw_session_id, pool)
        if not session:
            raise HTTPException(
                status_code=404,
                detail={"code": "SESSION_NOT_FOUND",
                        "message": "Session not found"},
            )
        session_id = raw_session_id
    else:
        ip, xff = _extract_ip(request)
        ua = request.headers.get("user-agent")
        new_id = await create_session(ip, ua, pool, xff)
        session_id = str(new_id)

    # ── Sanitize query ────────────────────────────────────────────────────────
    clean_query, err = sanitize_query(body.query)
    if err:
        raise HTTPException(
            status_code=400,
            detail={"code": err.code, "message": err.message},
        )

    # ── Run retrieval pipeline ────────────────────────────────────────────────
    reranked, history, prompt = await build_chat_pipeline(
        clean_query=clean_query,
        session_id=session_id,
        pool=pool,
        generate_fn=generate_fn,
        embed_fn=embed_fn,
        persona_text=request.app.state.persona_text,
    )

    chunk_ids = [c["id"] for c in reranked]

    # ── Stream LLM response ───────────────────────────────────────────────────
    async def event_stream():
        tokens: list[str] = []
        try:
            async for token in generate_fn(prompt, history):
                tokens.append(token)
                yield json.dumps({"success": True, "message": "token", "data": token})
        finally:
            full_answer = "".join(tokens)
            yield json.dumps({"success": True, "message": "done", "data": None})

            if full_answer:
                await save_message(session_id, "user", clean_query, [], None, pool)
                await save_message(session_id, "assistant", full_answer, chunk_ids, None, pool)
            await update_last_active(session_id, pool)

    response = EventSourceResponse(event_stream())
    response.headers["X-Session-Id"] = session_id
    return response
