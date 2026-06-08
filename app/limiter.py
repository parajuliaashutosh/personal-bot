from h11 import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    # Cloudflare
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return cf_ip

    # Other reverse proxies/load balancers
    if xff := request.headers.get("X-Forwarded-For"):
        # First IP is the original client
        return xff.split(",")[0].strip()

    # Fallback
    return request.client.host


limiter = Limiter(key_func=get_client_ip)
