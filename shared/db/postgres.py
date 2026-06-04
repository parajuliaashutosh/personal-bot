from __future__ import annotations

from pathlib import Path

import asyncpg
from asyncpg import Pool

from shared.config.settings import settings

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
        for migration in sorted(migrations_dir.glob("*.sql")):
            sql = migration.read_text()
            await conn.execute(sql)
