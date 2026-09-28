from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from shared.config.settings import settings


def get_client_ip(request: Request) -> str:
    # Cloudflare
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return cf_ip

    # Other reverse proxies/load balancers
    if xff := request.headers.get("X-Forwarded-For"):
        # First IP is the original client
        return xff.split(",")[0].strip()

    # Fallback
    return request.client.host if request.client else "unknown"


def retry_attempt(request: Request) -> int:
    """The client's self-reported retry number, clamped to what we advertised."""
    try:
        return max(0, min(int(request.headers.get("X-Retry-Attempt", "0")),
                          settings.client_max_retries))
    except (ValueError, TypeError):
        return 0


def question_cost(request: Request) -> int:
    """A retry of *our* failure is free — the user should not pay for it.

    Spoofing the header only buys a free pass on this limit; every request
    still hits `chat_burst_limit`, so the worst case is that ceiling.
    """
    return 0 if retry_attempt(request) > 0 else 1


limiter = Limiter(key_func=get_client_ip)
