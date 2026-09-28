from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.limiter import limiter, question_cost, retry_attempt
from retrieval.llm.errors import StreamTruncated
from retrieval.llm.reporting import set_error_hook
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
from shared.db.error_log import log_error
from shared.errors import (
    LLM_UNAVAILABLE,
    RETRIEVAL_FAILED,
    RETRYABLE_CODES,
    STREAM_TRUNCATED,
)
from shared.models.schema import ChatRequest
from shared.security.sanitizer import contains_profanity, sanitize_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_USER_FACING = {
    RETRIEVAL_FAILED: "I couldn't look that up just now.",
    LLM_UNAVAILABLE: "I'm having trouble reaching my assistant right now.",
    STREAM_TRUNCATED: "My answer got cut off partway through.",
}


def _sse(message: str, data) -> str:
    return json.dumps({"success": message != "error", "message": message, "data": data})


def _error_event(code: str, *, error_id: str | None, partial: bool, attempt: int) -> str:
    """Terminal SSE frame telling the client exactly what to do next.

    The frontend retries on `retryable` and stops at `max_retries`; `partial`
    tells it whether the bubble it is showing holds a half-finished answer that
    should be replaced rather than appended to.
    """
    retryable = code in RETRYABLE_CODES and attempt < settings.client_max_retries
    return _sse("error", {
        "code": code,
        "message": _USER_FACING.get(code, "Something went wrong on my side."),
        "retryable": retryable,
        "partial": partial,
        "attempt": attempt,
        "max_retries": settings.client_max_retries,
        "retry_after_ms": settings.client_retry_after_ms * (2 ** attempt),
        "error_id": error_id,
    })


def _bind_error_hook(pool, session_id: str, path: str, query: str, attempt: int):
    """Give the LLM provider chain a way to write into error_logs for this request."""

    async def hook(*, code: str, provider: str | None = None, attempt_no: int = 0,
                   recovered: bool = False, exc: BaseException | None = None,
                   partial_len: int | None = None, context: dict | None = None,
                   **extra) -> None:
        await log_error(
            pool,
            scope="llm_provider",
            code=code,
            provider=provider,
            attempt=extra.get("attempt", attempt_no),
            recovered=recovered,
            exc=exc,
            session_id=session_id,
            path=path,
            partial_len=partial_len,
            context={"query": query[:500], "client_attempt": attempt, **(context or {})},
        )

    set_error_hook(hook)


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
@limiter.limit(settings.chat_burst_limit)                      # hard ceiling, always charged
@limiter.limit(settings.chat_rate_limit, cost=question_cost)   # new questions only
async def chat(body: ChatRequest, request: Request):

    pool = request.app.state.pool
    generate_fn = request.app.state.generate_fn
    embed_fn = request.app.state.embed_fn

    # Client-driven retry: the frontend re-sends the same query and reports which
    # attempt this is, so backoff and give-up are decided server-side.
    attempt = retry_attempt(request)

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

    # ── Profanity check — save to DB but skip the full pipeline ──────────────
    if contains_profanity(clean_query):
        from shared.security.sanitizer import _PROFANITY_REPLY

        async def profanity_stream():
            await save_message(session_id, "user", clean_query, [], None, pool)
            await save_message(session_id, "assistant", _PROFANITY_REPLY, [], None, pool)
            await update_last_active(session_id, pool)
            yield _sse("token", _PROFANITY_REPLY)
            yield _sse("done", None)

        response = EventSourceResponse(profanity_stream())
        response.headers["X-Session-Id"] = session_id
        return response

    path = request.url.path
    _bind_error_hook(pool, session_id, path, clean_query, attempt)

    # ── Run retrieval pipeline ────────────────────────────────────────────────
    # A failure here happens before any bytes are streamed, so it is reported as
    # a one-frame SSE error rather than an HTTP 500 — the widget is already
    # listening on the stream and would otherwise just see the socket close.
    try:
        reranked, history, prompt = await build_chat_pipeline(
            clean_query=clean_query,
            session_id=session_id,
            pool=pool,
            generate_fn=generate_fn,
            embed_fn=embed_fn,
        )
    except Exception as exc:
        error_id = str(uuid.uuid4())
        logger.exception("Retrieval pipeline failed for session %s", session_id)
        await log_error(
            pool, scope="retrieval", code=RETRIEVAL_FAILED, exc=exc,
            session_id=session_id, path=path,
            context={"error_id": error_id, "query": clean_query[:500],
                     "client_attempt": attempt},
        )

        async def failed_stream():
            yield _error_event(RETRIEVAL_FAILED, error_id=error_id,
                               partial=False, attempt=attempt)

        response = EventSourceResponse(failed_stream())
        response.headers["X-Session-Id"] = session_id
        return response

    chunk_ids = [c["id"] for c in reranked]

    # ── Stream LLM response ───────────────────────────────────────────────────
    async def event_stream():
        tokens: list[str] = []
        failure_code: str | None = None
        failure_exc: BaseException | None = None
        error_id: str | None = None

        try:
            async for token in generate_fn(prompt, history):
                tokens.append(token)
                yield _sse("token", token)
        except StreamTruncated as exc:
            # Tokens already reached the client and no provider could finish the
            # thought. Keep what was sent and let the client decide to retry.
            failure_code, failure_exc = STREAM_TRUNCATED, exc
            tokens = [exc.partial] if exc.partial else tokens
        except asyncio.CancelledError:
            # Client hung up mid-answer. Keep what was generated, flagged, then
            # let the cancellation propagate so the connection tears down.
            if tokens:
                await save_message(session_id, "user", clean_query, [], None, pool,
                                   is_partial=True)
                await save_message(session_id, "assistant", "".join(tokens), chunk_ids,
                                   None, pool, is_partial=True,
                                   error_code="CLIENT_DISCONNECTED")
            raise
        except Exception as exc:
            failure_code = STREAM_TRUNCATED if tokens else LLM_UNAVAILABLE
            failure_exc = exc

        full_answer = "".join(tokens)

        if failure_code is not None:
            error_id = str(uuid.uuid4())
            logger.exception(
                "Chat stream failed (%s) for session %s after %d chars",
                failure_code, session_id, len(full_answer),
                exc_info=failure_exc,
            )
            await log_error(
                pool, scope="chat_stream", code=failure_code, exc=failure_exc,
                session_id=session_id, path=path, partial_len=len(full_answer),
                context={"error_id": error_id, "query": clean_query[:500],
                         "client_attempt": attempt,
                         "partial_text": full_answer[-2000:]},
            )

        # A half-finished answer is persisted for forensics but flagged, so it
        # never comes back as context on the next turn (see fetch_last_3).
        if full_answer:
            is_partial = failure_code is not None
            await save_message(session_id, "user", clean_query, [], None, pool,
                               is_partial=is_partial)
            await save_message(session_id, "assistant", full_answer, chunk_ids, None,
                               pool, is_partial=is_partial, error_code=failure_code)
        await update_last_active(session_id, pool)

        if failure_code is not None:
            yield _error_event(failure_code, error_id=error_id,
                               partial=bool(full_answer), attempt=attempt)
        else:
            yield _sse("done", None)

    response = EventSourceResponse(event_stream())
    response.headers["X-Session-Id"] = session_id
    return response
