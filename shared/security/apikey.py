from __future__ import annotations

from shared.config.settings import settings

_ADMIN_PREFIXES = ("/ingest", "/admin")
_CHAT_PREFIXES = ("/chat",)
_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def _route_type(path: str) -> str:
    """Returns 'admin', 'chat', or 'open'."""
    for prefix in _ADMIN_PREFIXES:
        if path.startswith(prefix):
            return "admin"
    for prefix in _CHAT_PREFIXES:
        if path.startswith(prefix):
            return "chat"
    return "open"


def validate_key_for_route(raw_key: str | None, path: str) -> tuple[bool, int]:
    """
    Returns (valid, http_status_code).
      401 — key missing entirely
      403 — key present but wrong for this route
      200 — valid
    """
    if path in _SKIP_PATHS:
        return True, 200

    route = _route_type(path)
    if route == "open":
        return True, 200

    if not raw_key:
        return False, 401

    if route == "admin":
        if raw_key == settings.admin_key:
            return True, 200
        return False, 403

    if route == "chat":
        if raw_key == settings.api_key:
            return True, 200
        return False, 403

    return True, 200
