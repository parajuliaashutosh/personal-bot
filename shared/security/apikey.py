import hashlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def validate_key(raw_key: str, session: AsyncSession) -> bool:
    hashed = hash_key(raw_key)
    result = await session.execute(
        text("SELECT 1 FROM api_keys WHERE key_hash = :hash AND active = TRUE"),
        {"hash": hashed},
    )
    return result.first() is not None
