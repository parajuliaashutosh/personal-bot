from __future__ import annotations

import logging
from pathlib import Path

import asyncpg
from asyncpg import Pool

from shared.config.settings import settings

logger = logging.getLogger(__name__)
_pool: Pool | None = None


async def get_pool() -> Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_migrations() -> None:
    pool = await get_pool()
    migrations_dir = Path(__file__).parent / "migrations"
    async with pool.acquire() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS _migrations "
            "(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())"
        )
        applied = {r["name"] for r in await conn.fetch("SELECT name FROM _migrations")}
        for migration in sorted(migrations_dir.glob("*.sql")):
            if migration.name in applied:
                continue
            await conn.execute(migration.read_text())
            await conn.execute("INSERT INTO _migrations (name) VALUES ($1)", migration.name)


async def seed_admin_user(pool: Pool) -> None:
    """Create the first admin from ADMIN_EMAIL / ADMIN_PASSWORD. Never overwrites an existing user."""
    if not (settings.admin_email and settings.admin_password):
        return
    from shared.security.auth import hash_password

    email = settings.admin_email.strip().lower()
    created = await pool.fetchval(
        "INSERT INTO admin_users (email, password_hash) VALUES ($1, $2)"
        " ON CONFLICT (email) DO NOTHING RETURNING id",
        email, hash_password(settings.admin_password),
    )
    if created:
        logger.info("Seeded admin user %s", email)
