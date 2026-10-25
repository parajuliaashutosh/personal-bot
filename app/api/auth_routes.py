from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.limiter import limiter
from app.responses import ok
from shared.config.settings import settings
from shared.security.auth import (
    DUMMY_HASH, create_access_token, decode_access_token, hash_refresh_token,
    new_refresh_token, token_from_headers, verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# The refresh cookie is only ever needed by /auth/refresh and /auth/logout.
_REFRESH_PATH = "/auth"
# Two tabs refreshing at once both present the same token; the slower one
# should fail quietly instead of looking like a stolen token.
_REUSE_GRACE_SECONDS = 30


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": message})


def _cookie_opts() -> dict:
    return {
        "httponly": True, "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite, "domain": settings.cookie_domain or None,
    }


def _set_auth_cookies(response: Response, access: str, ttl: int, refresh: str) -> None:
    # HttpOnly: page scripts can never read the tokens, so XSS cannot steal them.
    response.set_cookie(settings.cookie_name, access, max_age=ttl, path="/", **_cookie_opts())
    response.set_cookie(
        settings.refresh_cookie_name, refresh, max_age=settings.refresh_expire_days * 86400,
        path=_REFRESH_PATH, **_cookie_opts(),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.cookie_name, path="/", **_cookie_opts())
    response.delete_cookie(settings.refresh_cookie_name, path=_REFRESH_PATH, **_cookie_opts())


async def _store_refresh_token(conn, user_id, family_id) -> str:
    raw, digest = new_refresh_token()
    await conn.execute(
        "INSERT INTO admin_refresh_tokens (user_id, family_id, token_hash, expires_at)"
        " VALUES ($1, $2, $3, now() + make_interval(days => $4))",
        user_id, family_id, digest, settings.refresh_expire_days,
    )
    return raw


def _from_allowed_origin(request: Request) -> bool:
    return request.headers.get("Origin") in settings.cors_origins


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, body: LoginRequest):
    pool = request.app.state.pool
    row = await pool.fetchrow(
        "SELECT id, email, password_hash FROM admin_users WHERE email = $1",
        body.email.strip().lower(),
    )
    ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH)
    if not row or not ok:
        raise _unauthorized("Invalid email or password")

    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("UPDATE admin_users SET last_login_at = now() WHERE id = $1", row["id"])
        await conn.execute(
            "DELETE FROM admin_refresh_tokens WHERE user_id = $1 AND expires_at < now()", row["id"])
        refresh = await _store_refresh_token(conn, row["id"], uuid.uuid4())

    token, ttl = create_access_token(str(row["id"]), row["email"])
    _set_auth_cookies(response, token, ttl, refresh)
    return ok({"email": row["email"], "expires_in": ttl})


@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh(request: Request, response: Response):
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw or not _from_allowed_origin(request):
        raise _unauthorized("Missing refresh token")

    failure = None
    async with request.app.state.pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            "SELECT t.id, t.user_id, t.family_id, t.expires_at < now() AS expired,"
            " t.revoked_at, t.revoked_at > now() - make_interval(secs => $2) AS recently_revoked,"
            " u.email"
            " FROM admin_refresh_tokens t JOIN admin_users u ON u.id = t.user_id"
            " WHERE t.token_hash = $1 FOR UPDATE OF t",
            hash_refresh_token(raw), _REUSE_GRACE_SECONDS,
        )
        if not row or row["expired"]:
            failure = "Refresh token expired"
        elif row["revoked_at"]:
            failure = "Refresh token already used"
            if not row["recently_revoked"]:
                # A rotated-out token came back: assume it leaked and end the whole login.
                await conn.execute(
                    "UPDATE admin_refresh_tokens SET revoked_at = now()"
                    " WHERE family_id = $1 AND revoked_at IS NULL", row["family_id"])
        else:
            await conn.execute(
                "UPDATE admin_refresh_tokens SET revoked_at = now() WHERE id = $1", row["id"])
            new_refresh = await _store_refresh_token(conn, row["user_id"], row["family_id"])
    if failure:
        raise _unauthorized(failure)

    token, ttl = create_access_token(str(row["user_id"]), row["email"])
    _set_auth_cookies(response, token, ttl, new_refresh)
    return ok({"email": row["email"], "expires_in": ttl})


@router.post("/logout")
async def logout(request: Request, response: Response):
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw and _from_allowed_origin(request):
        await request.app.state.pool.execute(
            "UPDATE admin_refresh_tokens SET revoked_at = now()"
            " WHERE revoked_at IS NULL AND family_id ="
            " (SELECT family_id FROM admin_refresh_tokens WHERE token_hash = $1)",
            hash_refresh_token(raw),
        )
    _clear_auth_cookies(response)
    return ok(message="Logged out", code="LOGGED_OUT")


@router.get("/me")
async def me(request: Request):
    claims = decode_access_token(token_from_headers(
        request.headers.get("Authorization"),
        request.cookies.get(settings.cookie_name)) or "")
    if not claims:
        raise _unauthorized("Invalid or expired token")
    return ok({"email": claims["email"],
               "expires_in": max(0, claims["exp"] - int(time.time()))})
