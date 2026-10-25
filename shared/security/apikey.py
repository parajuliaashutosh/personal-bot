from __future__ import annotations

from shared.config.settings import settings
from shared.security.auth import decode_access_token

_ADMIN_PREFIXES = ("/ingest", "/admin")
_OPEN_PREFIXES = ("/auth",)  # handlers authenticate themselves
_CHAT_PREFIXES = ("/chat",)
_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def _route_type(path: str) -> str:
    """Returns 'admin', 'chat', or 'open'."""
    for prefix in _OPEN_PREFIXES:
        if path.startswith(prefix):
            return "open"
    for prefix in _ADMIN_PREFIXES:
        if path.startswith(prefix):
            return "admin"
    for prefix in _CHAT_PREFIXES:
        if path.startswith(prefix):
            return "chat"
    return "open"


def validate_key_for_route(
    raw_key: str | None, path: str, token: str | None = None
) -> tuple[bool, int]:
    """
    Returns (valid, http_status_code).
      Admin routes need a valid JWT; chat routes need API_KEY.
      401 — credentials missing
      403 — credentials present but wrong for this route
      200 — valid
    """
    if path in _SKIP_PATHS:
        return True, 200

    route = _route_type(path)
    if route == "open":
        return True, 200

    if route == "admin":
        if not token:
            return False, 401
        return (True, 200) if decode_access_token(token) else (False, 403)

    if route == "chat":
        if not raw_key:
            return False, 401
        return (True, 200) if raw_key == settings.api_key else (False, 403)

    return True, 200
