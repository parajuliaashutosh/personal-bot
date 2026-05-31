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
    migrations_file = Path(__file__).parent / "migrations" / "001_initial.sql"
    sql = migrations_file.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)
