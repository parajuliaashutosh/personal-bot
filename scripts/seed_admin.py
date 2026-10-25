from __future__ import annotations

import asyncio
import getpass
import sys

from shared.config.settings import settings
from shared.db.postgres import close_pool, get_pool, run_migrations
from shared.security.auth import hash_password

MIN_PASSWORD_LENGTH = 12


def _read_password(email: str) -> str:
    if settings.admin_password:
        return settings.admin_password
    if not sys.stdin.isatty():
        sys.exit("error: set ADMIN_PASSWORD or run this command in a terminal")
    first = getpass.getpass(f"Password for {email}: ")
    if getpass.getpass("Repeat password: ") != first:
        sys.exit("error: passwords do not match")
    return first


async def _upsert(email: str, password: str) -> bool:
    """Returns True when the account was created, False when its password was replaced."""
    await run_migrations()  # the admin_users table exists only after migrations
    pool = await get_pool()
    try:
        async with pool.acquire() as conn, conn.transaction():
            created = bool(await conn.fetchval(
                "INSERT INTO admin_users (email, password_hash) VALUES ($1, $2) "
                "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash "
                "RETURNING (xmax = 0)",
                email, hash_password(password),
            ))
            # A new password signs out every existing login.
            await conn.execute(
                "UPDATE admin_refresh_tokens SET revoked_at = now() WHERE revoked_at IS NULL"
                " AND user_id = (SELECT id FROM admin_users WHERE email = $1)", email)
        return created
    finally:
        await close_pool()


def main() -> None:
    email = settings.admin_email.strip().lower()
    if "@" not in email:
        sys.exit("error: set ADMIN_EMAIL in .env to the admin email")

    password = _read_password(email)
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"error: password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password.encode()) > 72:
        sys.exit("error: password must be at most 72 bytes (bcrypt limit)")

    created = asyncio.run(_upsert(email, password))
    print(f"{'Created' if created else 'Updated password for'} admin {email}")


if __name__ == "__main__":
    main()
