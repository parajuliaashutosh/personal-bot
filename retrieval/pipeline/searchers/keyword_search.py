from __future__ import annotations

import json

from asyncpg import Pool


def _meta(value) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(value)


async def keyword_search(
    keywords: list[str],
    limit: int,
    pool: Pool,
) -> list[dict]:
    if not keywords:
        return []

    query_str = " ".join(keywords)

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
            "metadata": _meta(row["metadata"]),
            "score": float(row["score"]),
            "source": "keyword",
        }
        for row in rows
    ]
