from __future__ import annotations

import uuid

from asyncpg import Pool


async def keyword_search(
    keywords: list[str],
    document_id: uuid.UUID | None,
    limit: int,
    pool: Pool,
) -> list[dict]:
    if not keywords:
        return []

    query_str = " ".join(keywords)

    if document_id:
        rows = await pool.fetch(
            "SELECT id, document_id, text, section_path, page_start, page_end, token_count, metadata,"
            "       ts_rank(to_tsvector('english', text), plainto_tsquery('english', $1)) AS score"
            " FROM chunks"
            " WHERE document_id = $2"
            "   AND to_tsvector('english', text) @@ plainto_tsquery('english', $1)"
            " ORDER BY score DESC LIMIT $3",
            query_str, document_id, limit,
        )
    else:
        rows = await pool.fetch(
            "SELECT id, document_id, text, section_path, page_start, page_end, token_count, metadata,"
            "       ts_rank(to_tsvector('english', text), plainto_tsquery('english', $1)) AS score"
            " FROM chunks"
            " WHERE to_tsvector('english', text) @@ plainto_tsquery('english', $1)"
            " ORDER BY score DESC LIMIT $2",
            query_str, limit,
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
            "metadata": dict(row["metadata"]) if row["metadata"] else {},
            "score": float(row["score"]),
            "source": "keyword",
        }
        for row in rows
    ]
