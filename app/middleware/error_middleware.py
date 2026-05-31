from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.errors import INTERNAL_ERROR

logger = logging.getLogger(__name__)


async def error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": INTERNAL_ERROR,
                    "message": "An internal server error occurred",
                    "details": None,
                }
            },
        )
