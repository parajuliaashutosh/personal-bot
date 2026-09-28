from __future__ import annotations

import json
import uuid
from uuid import UUID

from asyncpg import Pool


async def fetch_last_3(session_id: str, pool: Pool) -> list[dict[str, str]]:
    """Recent turns for prompt context.

    Partial turns are excluded: feeding a half-finished answer back as history
    makes the model continue a broken thought instead of answering afresh.
    """
    rows = await pool.fetch(
        "SELECT role, content FROM messages"
        " WHERE session_id = $1 AND NOT is_partial"
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
    is_partial: bool = False,
    error_code: str | None = None,
) -> None:
    await pool.execute(
        "INSERT INTO messages"
        " (session_id, role, content, retrieved_chunk_ids, rerank_scores,"
        "  is_partial, error_code)"
        " VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)",
        UUID(session_id),
        role,
        content,
        chunk_ids if chunk_ids else None,
        json.dumps(rerank_scores) if rerank_scores is not None else None,
        is_partial,
        error_code,
    )
