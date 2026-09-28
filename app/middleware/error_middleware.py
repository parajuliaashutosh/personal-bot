from __future__ import annotations

import logging
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.db.error_log import log_error
from shared.errors import INTERNAL_ERROR

logger = logging.getLogger(__name__)


async def error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        error_id = str(uuid.uuid4())
        logger.exception("Unhandled exception on %s %s: %s",
                         request.method, request.url.path, exc)
        # Streaming routes handle their own failures inside the SSE body — this
        # only catches errors raised before a response has started.
        await log_error(
            getattr(request.app.state, "pool", None),
            scope="http",
            code=INTERNAL_ERROR,
            exc=exc,
            path=request.url.path,
            status_code=500,
            session_id=request.headers.get("X-Session-Id"),
            context={"error_id": error_id, "method": request.method},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": INTERNAL_ERROR,
                    "message": "An internal server error occurred",
                    "details": {"error_id": error_id},
                }
            },
        )
