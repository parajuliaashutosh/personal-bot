from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from retrieval.memory.chat_history import fetch_last_3, save_message
from retrieval.memory.session import (
    create_session,
    enrich_session_geo,
    get_session,
    update_last_active,
    validate_session_id,
)
from retrieval.pipeline.context_builder import build_context
from retrieval.pipeline.merger import merge
from retrieval.pipeline.postprocessor import postprocess
from retrieval.pipeline.prompt_builder import build_prompt
from retrieval.pipeline.query_expansion import expand_query
from retrieval.pipeline.query_understanding import understand_query
from retrieval.pipeline.ranker import rank
from retrieval.pipeline.reranker import rerank
from retrieval.pipeline.searchers.keyword_search import keyword_search
from retrieval.pipeline.searchers.memory_search import memory_search
from retrieval.pipeline.searchers.vector_search import vector_search
from shared.config.settings import settings
from shared.models.schema import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/session", status_code=201)
async def create_chat_session(
    request: Request,
    background_tasks: BackgroundTasks,
):
    pool = request.app.state.pool
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    session_id = await create_session(ip, user_agent, pool)

    if ip and settings.ipinfo_api_key:
        background_tasks.add_task(enrich_session_geo, str(session_id), ip, pool)

    response = JSONResponse(
        status_code=201,
        content={"success": True, "message": "session created", "data": {"session_id": str(session_id)}},
    )
    response.headers["X-Session-Id"] = str(session_id)
    return response


@router.post("/")
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
                detail={"code": "SESSION_INVALID_ID", "message": "Invalid session ID format"},
            )
        session = await get_session(raw_session_id, pool)
        if not session:
            raise HTTPException(
                status_code=404,
                detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
            )
        session_id = raw_session_id
    else:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        new_id = await create_session(ip, ua, pool)
        session_id = str(new_id)

    # ── Sanitize ──────────────────────────────────────────────────────────────
    clean_query, err = sanitize_query(body.query)
    if err:
        raise HTTPException(
            status_code=400,
            detail={"code": err.code, "message": err.message},
        )

    # ── Retrieval pipeline (all blocking work before streaming) ───────────────
    query_ctx, _ = await understand_query(clean_query)
    variations = await expand_query(clean_query, query_ctx, generate_fn)

    all_queries = [clean_query] + variations
    embeddings = await embed_fn(all_queries[:2])

    vector_batches = await asyncio.gather(
        *[vector_search(emb, 20, pool) for emb in embeddings]
    )
    vector_results = [chunk for batch in vector_batches for chunk in batch]

    kw_results, mem_results = await asyncio.gather(
        keyword_search(query_ctx["keywords"], 20, pool),
        memory_search(session_id, pool),
    )

    candidates = merge(vector_results + kw_results + mem_results)
    ranked = rank(candidates, query_ctx)
    reranked = await rerank(clean_query, ranked[:20], generate_fn)

    context_str = build_context(reranked, settings.context_token_limit)
    history = await fetch_last_3(session_id, pool)
    prompt = build_prompt(clean_query, context_str, request.app.state.persona_text)

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
