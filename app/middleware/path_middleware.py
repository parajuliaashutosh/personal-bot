from __future__ import annotations

from fastapi import Request


async def trailing_slash_middleware(request: Request, call_next):
    # strip trailing slash
    path = request.scope["path"]
    if len(path) > 1 and path.endswith("/"):
        request.scope["path"] = path.rstrip("/") or "/"
    return await call_next(request)
