from __future__ import annotations

import json
import logging
import traceback
from uuid import UUID

from asyncpg import Pool

logger = logging.getLogger(__name__)

_MAX_MESSAGE = 4000
_MAX_STACK = 20000


def _coerce_session_id(session_id: str | UUID | None) -> UUID | None:
    if session_id is None:
        return None
    if isinstance(session_id, UUID):
        return session_id
    try:
        return UUID(session_id)
    except (ValueError, AttributeError, TypeError):
        return None


async def log_error(
    pool: Pool | None,
    *,
    scope: str,
    code: str,
    message: str = "",
    exc: BaseException | None = None,
    provider: str | None = None,
    attempt: int = 0,
    recovered: bool = False,
    session_id: str | UUID | None = None,
    path: str | None = None,
    status_code: int | None = None,
    partial_len: int | None = None,
    context: dict | None = None,
    with_stack: bool = True,
) -> None:
    """Record one error in `error_logs`.

    Never raises: logging an error must not be able to break the request that
    is already failing. Falls back to the application log if the insert fails.
    """
    if exc is not None and not message:
        message = f"{type(exc).__name__}: {exc}"

    stack = None
    if exc is not None and with_stack:
        stack = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )[:_MAX_STACK]

    try:
        if pool is None:
            raise RuntimeError("no db pool available")
        await pool.execute(
            "INSERT INTO error_logs"
            " (scope, code, message, exc_type, provider, attempt, recovered,"
            "  session_id, path, status_code, partial_len, context, stack)"
            " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13)",
            scope,
            code,
            (message or "")[:_MAX_MESSAGE],
            type(exc).__name__ if exc is not None else None,
            provider,
            attempt,
            recovered,
            _coerce_session_id(session_id),
            path,
            status_code,
            partial_len,
            json.dumps(context or {}),
            stack,
        )
    except Exception:  # noqa: BLE001 — last-resort sink
        logger.exception(
            "Failed to persist error_log (scope=%s code=%s provider=%s): %s",
            scope, code, provider, message,
        )


async def list_errors(
    pool: Pool,
    *,
    limit: int = 100,
    offset: int = 0,
    code: str | None = None,
    scope: str | None = None,
    session_id: str | None = None,
    unrecovered_only: bool = False,
) -> list[dict]:
    clauses: list[str] = []
    args: list = []

    if code:
        args.append(code)
        clauses.append(f"code = ${len(args)}")
    if scope:
        args.append(scope)
        clauses.append(f"scope = ${len(args)}")
    if session_id and (sid := _coerce_session_id(session_id)):
        args.append(sid)
        clauses.append(f"session_id = ${len(args)}")
    if unrecovered_only:
        clauses.append("NOT recovered")

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    args.extend([limit, offset])

    rows = await pool.fetch(
        f"SELECT * FROM error_logs{where}"
        f" ORDER BY occurred_at DESC LIMIT ${len(args) - 1} OFFSET ${len(args)}",
        *args,
    )
    return [dict(r) for r in rows]


async def error_summary(pool: Pool, hours: int = 24) -> list[dict]:
    """Rollup of the last N hours — what is breaking, how often, and how often it self-healed."""
    rows = await pool.fetch(
        "SELECT scope, code, provider,"
        "       count(*) AS total,"
        "       count(*) FILTER (WHERE recovered) AS recovered,"
        "       max(occurred_at) AS last_seen"
        " FROM error_logs"
        " WHERE occurred_at > now() - ($1 || ' hours')::interval"
        " GROUP BY scope, code, provider"
        " ORDER BY total DESC",
        str(hours),
    )
    return [dict(r) for r in rows]
