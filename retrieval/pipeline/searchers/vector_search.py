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


async def vector_search(
    embedding: list[float],
    document_id: uuid.UUID | None,
    limit: int,
    pool: Pool,
) -> list[dict]:
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    if document_id:
        rows = await pool.fetch(
            "SELECT id, document_id, text, section_path, page_start, page_end, token_count, metadata,"
            "       1 - (embedding <=> $1::vector) AS score"
            " FROM chunks WHERE document_id = $2"
            " ORDER BY embedding <=> $1::vector LIMIT $3",
            embedding_str, document_id, limit,
        )
    else:
        rows = await pool.fetch(
            "SELECT id, document_id, text, section_path, page_start, page_end, token_count, metadata,"
            "       1 - (embedding <=> $1::vector) AS score"
            " FROM chunks"
            " ORDER BY embedding <=> $1::vector LIMIT $2",
            embedding_str, limit,
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
            "score": float(row["score"]),
            "source": "vector",
        }
        for row in rows
    ]
