from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.security.apikey import validate_key_for_route


async def apikey_middleware(request: Request, call_next):
    raw_key = request.headers.get("X-API-Key")
    valid, status = validate_key_for_route(raw_key, request.url.path)

    if not valid:
        message = "X-API-Key header is required" if status == 401 else "Invalid API key for this route"
        return JSONResponse(
            status_code=status,
            content={"error": {"code": "UNAUTHORIZED", "message": message, "details": None}},
        )

    return await call_next(request)
