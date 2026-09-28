from __future__ import annotations

from fastapi import APIRouter, Query, Request

from shared.db.error_log import error_summary, list_errors

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/errors")
async def get_errors(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    code: str | None = None,
    scope: str | None = None,
    session_id: str | None = None,
    unrecovered_only: bool = False,
):
    """Raw error log, newest first.

    `unrecovered_only=true` hides failures that a retry or fallback already
    rescued — those are noise unless you are tuning the chain.
    """
    rows = await list_errors(
        request.app.state.pool,
        limit=limit,
        offset=offset,
        code=code,
        scope=scope,
        session_id=session_id,
        unrecovered_only=unrecovered_only,
    )
    return {"success": True, "message": "ok", "data": {"errors": rows, "count": len(rows)}}


@router.get("/errors/summary")
async def get_error_summary(
    request: Request,
    hours: int = Query(24, ge=1, le=24 * 30),
):
    """What is breaking, how often, and how often it self-healed."""
    rows = await error_summary(request.app.state.pool, hours)
    return {"success": True, "message": "ok",
            "data": {"window_hours": hours, "buckets": rows}}


@router.get("/messages/partial")
async def get_partial_messages(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
):
    """Answers that reached the user half-finished — the user-visible symptom."""
    rows = await request.app.state.pool.fetch(
        "SELECT id, session_id, role, left(content, 400) AS preview,"
        "       length(content) AS length, error_code, created_at"
        " FROM messages WHERE is_partial AND role = 'assistant'"
        " ORDER BY created_at DESC LIMIT $1",
        limit,
    )
    return {"success": True, "message": "ok",
            "data": {"messages": [dict(r) for r in rows], "count": len(rows)}}
