from __future__ import annotations

import hashlib
import secrets
import time

import bcrypt
import jwt

from shared.config.settings import settings

_ALG = "HS256"


def hash_password(password: str) -> str:
    """bcrypt stores the salt inside the hash, so one string is all we keep."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except ValueError:  # malformed hash, or password longer than bcrypt's 72 bytes
        return False

DUMMY_HASH = hash_password("not-a-real-password")


def create_access_token(user_id: str, email: str) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    ttl = settings.jwt_expire_minutes * 60
    now = int(time.time())
    token = jwt.encode(
        {"sub": user_id, "email": email, "role": "admin", "iat": now, "exp": now + ttl},
        settings.jwt_secret, algorithm=_ALG,
    )
    return token, ttl


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw, sha256). Only the hash is stored, so a database leak yields no usable tokens."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict | None:
    try:
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[_ALG],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    return claims if claims.get("role") == "admin" else None


def bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization[:7].lower() == "bearer ":
        return authorization[7:].strip() or None
    return None


def token_from_headers(authorization: str | None, cookie: str | None) -> str | None:
    """Bearer header wins (scripts); otherwise the HttpOnly login cookie."""
    return bearer_token(authorization) or cookie or None
