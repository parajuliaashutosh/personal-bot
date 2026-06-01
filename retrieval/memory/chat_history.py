from __future__ import annotations

import json
import uuid
from uuid import UUID

from asyncpg import Pool


async def fetch_last_3(session_id: str, pool: Pool) -> list[dict[str, str]]:
    rows = await pool.fetch(
        "SELECT role, content FROM messages"
        " WHERE session_id = $1"
        " ORDER BY created_at DESC LIMIT 3",
        UUID(session_id),
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def save_message(
    session_id: str,
    role: str,
    content: str,
    chunk_ids: list[UUID],
    rerank_scores: dict | None,
    pool: Pool,
) -> None:
    await pool.execute(
        "INSERT INTO messages (session_id, role, content, retrieved_chunk_ids, rerank_scores)"
        " VALUES ($1, $2, $3, $4, $5::jsonb)",
        UUID(session_id),
        role,
        content,
        chunk_ids if chunk_ids else None,
        json.dumps(rerank_scores) if rerank_scores is not None else None,
    )
