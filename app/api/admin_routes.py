from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from app.responses import ok, page
from shared.db.error_log import error_summary, list_errors
from shared.errors import SESSION_INVALID_ID, SESSION_NOT_FOUND

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
    return ok(page(rows, limit=limit, offset=offset))


@router.get("/errors/summary")
async def get_error_summary(
    request: Request,
    hours: int = Query(24, ge=1, le=24 * 30),
):
    """What is breaking, how often, and how often it self-healed."""
    rows = await error_summary(request.app.state.pool, hours)
    return ok(page(rows, window_hours=hours))


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
    return ok(page([dict(r) for r in rows], limit=limit))


# ipinfo stores "lat,lng" in geo_raw->>'loc'; NULL when geo lookup was skipped or malformed.
_LOC = "CASE WHEN {t}geo_raw->>'loc' ~ '^-?[0-9]+(\\.[0-9]+)?,-?[0-9]+(\\.[0-9]+)?$' THEN {t}geo_raw->>'loc' END"
_LAT = f"split_part({_LOC}, ',', 1)::float8"
_LNG = f"split_part({_LOC}, ',', 2)::float8"


def _session_uuid(session_id: str) -> UUID:
    try:
        return UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={
            "code": SESSION_INVALID_ID, "message": "Invalid session id"})


OVERVIEW_MAX_AGE = "60 seconds"
_overview_refresh_lock = asyncio.Lock()


async def _refresh_overview(pool) -> None:
    async with _overview_refresh_lock:
        await pool.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY admin_overview_mv")


async def _overview_row(pool, *, force: bool = False) -> dict:
    row = await pool.fetchrow(
        "SELECT *, now() - refreshed_at > interval '" + OVERVIEW_MAX_AGE + "' AS stale"
        " FROM admin_overview_mv WHERE id = 1"
    )
    if force or row["stale"]:
        await _refresh_overview(pool)
        row = await pool.fetchrow("SELECT * FROM admin_overview_mv WHERE id = 1")
    data = dict(row)
    data.pop("id", None)
    data.pop("stale", None)
    if isinstance(data.get("errors_by_scope"), str):  # asyncpg returns jsonb as text
        data["errors_by_scope"] = json.loads(data["errors_by_scope"])
    return data


@router.get("/overview")
async def get_overview(request: Request):
    """Headline numbers for the dashboard, read from the materialized view."""
    return ok(await _overview_row(request.app.state.pool))


@router.post("/overview/refresh")
async def refresh_overview(request: Request):
    """Recompute the dashboard numbers now (the Refresh button)."""
    data = await _overview_row(request.app.state.pool, force=True)
    return ok(data, message="Overview refreshed", code="REFRESHED")


@router.get("/sessions")
async def get_sessions(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Sessions, most recently active first, with a message count and last question."""
    rows = await request.app.state.pool.fetch(
        "SELECT s.id, s.created_at, s.last_active, s.ip, s.ip_city, s.ip_region,"
        "       s.ip_country, s.user_agent,"
        f"       {_LAT.format(t='s.')} AS lat, {_LNG.format(t='s.')} AS lng,"
        "       count(m.id) AS message_count,"
        "       count(m.id) FILTER (WHERE m.is_partial) AS partial_count,"
        "       (SELECT left(content, 160) FROM messages"
        "         WHERE session_id = s.id AND role = 'user'"
        "         ORDER BY created_at DESC LIMIT 1) AS last_question,"
        "       (SELECT count(*) FROM error_logs e"
        "         WHERE e.session_id = s.id AND NOT e.recovered) AS unrecovered_errors"
        " FROM sessions s LEFT JOIN messages m ON m.session_id = s.id"
        " GROUP BY s.id ORDER BY s.last_active DESC LIMIT $1 OFFSET $2",
        limit, offset,
    )
    total = await request.app.state.pool.fetchval("SELECT count(*) FROM sessions")
    return ok(page([dict(r) for r in rows], total=total, limit=limit, offset=offset))


@router.get("/sessions/{session_id}")
async def get_session_detail(request: Request, session_id: str):
    """One session and its full conversation, oldest message first."""
    sid = _session_uuid(session_id)
    pool = request.app.state.pool
    session = await pool.fetchrow(
        "SELECT id, created_at, last_active, ip, ip_forwarded_for, ip_city, ip_region,"
        "       ip_country, ip_asn, ip_timezone, user_agent,"
        f"       {_LAT.format(t='')} AS lat, {_LNG.format(t='')} AS lng"
        " FROM sessions WHERE id = $1", sid)
    if session is None:
        raise HTTPException(status_code=404, detail={
            "code": SESSION_NOT_FOUND, "message": "Session not found"})
    messages = await pool.fetch(
        "SELECT id, role, content, is_partial, error_code, created_at,"
        "       coalesce(array_length(retrieved_chunk_ids, 1), 0) AS chunk_count"
        " FROM messages WHERE session_id = $1 ORDER BY created_at ASC", sid)
    errors = await list_errors(pool, limit=100, session_id=session_id)
    return ok({
        "session": dict(session),
        "messages": [dict(m) for m in messages],
        "errors": errors,
    })


@router.get("/messages/recent")
async def get_recent_messages(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    role: str | None = Query(None, pattern="^(user|assistant)$"),
):
    """Latest messages across every session, newest first."""
    rows = await request.app.state.pool.fetch(
        "SELECT id, session_id, role, left(content, 600) AS preview,"
        "       length(content) AS length, is_partial, error_code, created_at"
        " FROM messages WHERE ($2::text IS NULL OR role = $2)"
        " ORDER BY created_at DESC LIMIT $1",
        limit, role,
    )
    return ok(page([dict(r) for r in rows], limit=limit))
