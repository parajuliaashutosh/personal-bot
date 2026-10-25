from __future__ import annotations

from fastapi import Request

from app.responses import fail
from shared.config.settings import settings
from shared.security.apikey import validate_key_for_route
from shared.security.auth import bearer_token, token_from_headers


async def apikey_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    raw_key = request.headers.get("X-API-Key")
    authorization = request.headers.get("Authorization")
    cookie = request.cookies.get(settings.cookie_name)
    token = token_from_headers(authorization, cookie)

    # A cookie is sent by the browser automatically, so on state-changing
    # requests it only counts when the request comes from an allowed origin.
    if (cookie and not bearer_token(authorization)
            and request.method not in ("GET", "HEAD")
            and request.headers.get("Origin") not in settings.cors_origins):
        token = None
    valid, status = validate_key_for_route(raw_key, request.url.path, token)

    if not valid:
        message = "Missing credentials: X-API-Key for chat, Bearer token for admin" if status == 401 else "Invalid credentials for this route"
        return fail(status, "UNAUTHORIZED" if status == 401 else "FORBIDDEN",
                    message, request=request)

    return await call_next(request)
