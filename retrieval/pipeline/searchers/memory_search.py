from __future__ import annotations

import json
import uuid

from asyncpg import Pool


def _meta(value) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(value)


async def memory_search(session_id: str, pool: Pool) -> list[dict]:
    """Return recent assistant messages from this session as low-weight candidates."""
    rows = await pool.fetch(
        "SELECT m.retrieved_chunk_ids FROM messages m"
        " WHERE m.session_id = $1 AND m.role = 'assistant'"
        "   AND m.retrieved_chunk_ids IS NOT NULL"
        " ORDER BY m.created_at DESC LIMIT 3",
        uuid.UUID(session_id),
    )

    if not rows:
        return []

    chunk_ids: list[uuid.UUID] = []
    for row in rows:
        ids = row["retrieved_chunk_ids"]
        if ids:
            chunk_ids.extend(ids)

    if not chunk_ids:
        return []

    chunk_rows = await pool.fetch(
        "SELECT id, document_id, text, section_path, page_start, page_end, token_count, metadata"
        " FROM chunks WHERE id = ANY($1::uuid[])",
        chunk_ids,
    )

    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "text": row["text"],
            "section_path": list(row["section_path"] or []),
            "page_start": row["page_start"],
            "page_end": row["page_end"],
            "token_count": row["token_count"],
            "metadata": _meta(row["metadata"]),
            "score": 0.4,
            "source": "memory",
        }
        for row in chunk_rows
    ]
