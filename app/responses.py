"""One JSON envelope for every non-streaming response, success or error.

    {"success": bool, "code": str, "message": str, "data": ... | null, "error": {"details": ...} | null}

Exactly one of `data` / `error` is filled. Clients branch on `code`, show `message`.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

# Fallback code/message when an HTTPException carries no code of its own.
_STATUS_DEFAULTS: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "Bad request"),
    401: ("UNAUTHORIZED", "Authentication required"),
    403: ("FORBIDDEN", "Not allowed"),
    404: ("NOT_FOUND", "Route not found"),
    405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
    409: ("CONFLICT", "Conflict"),
    413: ("PAYLOAD_TOO_LARGE", "Payload too large"),
    422: ("VALIDATION_ERROR", "Invalid request"),
    429: ("RATE_LIMITED", "Too many requests. Slow down."),
    500: ("INTERNAL_ERROR", "An internal server error occurred"),
    503: ("SERVICE_UNAVAILABLE", "Service unavailable"),
}


def ok(data: Any = None, message: str = "ok", code: str = "OK") -> dict:
    return {"success": True, "code": code, "message": message, "data": data, "error": None}


def page(items: list, *, total: int | None = None, limit: int | None = None,
         offset: int | None = None, **extra) -> dict:
    """`data` shape for list endpoints."""
    return {"items": items, "count": len(items), "total": total,
            "limit": limit, "offset": offset, **extra}


def fail(
    status_code: int,
    code: str | None = None,
    message: str | None = None,
    details: Any = None,
    *,
    request: Request | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    default_code, default_message = _STATUS_DEFAULTS.get(
        status_code, (f"HTTP_{status_code}", "Request failed"))
    code = code or default_code
    if request is not None:
        # error_middleware logs this instead of a generic HTTP_<status>.
        request.state.error_code = code
        request.state.error_message = message or default_message
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=jsonable_encoder({
            "success": False,
            "code": code,
            "message": message or default_message,
            "data": None,
            "error": {"details": details},
        }),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:

    if isinstance(exc.detail, dict):
        return fail(exc.status_code, exc.detail.get("code"), exc.detail.get("message"),
                    exc.detail.get("details"), request=request, headers=exc.headers)
    details = ({"path": request.url.path, "method": request.method}
               if exc.status_code in (404, 405) else None)
    return fail(exc.status_code, details=details, request=request, headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg", "")}
        for e in exc.errors()
    ]
    return fail(422, details={"fields": fields}, request=request)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return fail(429, details={"limit": str(exc.detail)}, request=request)


def install(app) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
