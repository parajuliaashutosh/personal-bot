import hashlib

from asyncpg import Pool


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def validate_key(raw_key: str, pool: Pool) -> bool:
    hashed = hash_key(raw_key)
    row = await pool.fetchrow(
        "SELECT 1 FROM api_keys WHERE key_hash = $1 AND active = TRUE", hashed
    )
    return row is not None
