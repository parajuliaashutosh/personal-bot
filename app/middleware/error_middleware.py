from __future__ import annotations

import asyncio
import logging

from fastapi import Request

from app.responses import fail
from shared.db.error_log import log_error
from shared.errors import INTERNAL_ERROR

logger = logging.getLogger(__name__)

_pending: set[asyncio.Task] = set()


def _log_in_background(request: Request, **fields) -> None:
    """Write to error_logs without making the response wait on the insert."""
    task = asyncio.create_task(log_error(
        getattr(request.app.state, "pool", None),
        path=request.url.path,
        session_id=request.headers.get("X-Session-Id"),
        **fields,
    ))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled exception on %s %s: %s",
                         request.method, request.url.path, exc)

        _log_in_background(
            request,
            scope="http",
            code=INTERNAL_ERROR,
            exc=exc,
            status_code=500,
            context={"method": request.method},
        )
        return fail(500, INTERNAL_ERROR)

    status = response.status_code
    if status >= 400:
        reason = getattr(request.state, "error_message", None)
        _log_in_background(
            request,
            scope="client" if status < 500 else "http",
            code=getattr(request.state, "error_code", None) or f"HTTP_{status}",
            message=f"{request.method} {request.url.path} -> {status}"
                    + (f": {reason}" if reason else ""),
            status_code=status,
            with_stack=False,
            context={
                "method": request.method,
                "query": str(request.url.query) or None,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )
    return response
