from __future__ import annotations

import uuid

from asyncpg import Pool


async def metadata_search(filters: dict, pool: Pool) -> list[dict]:
    """Filter chunks by document_id and/or language tag in metadata."""
    if not filters:
        return []

    clauses: list[str] = []
    params: list = []
    idx = 1

    doc_id: uuid.UUID | None = filters.get("document_id")
    if doc_id:
        clauses.append(f"document_id = ${idx}")
        params.append(doc_id)
        idx += 1

    language: str | None = filters.get("language")
    if language:
        clauses.append(f"metadata->>'language' = ${idx}")
        params.append(language)
        idx += 1

    if not clauses:
        return []

    where = " AND ".join(clauses)
    rows = await pool.fetch(
        f"SELECT id, document_id, text, section_path, page_start, page_end, token_count, metadata"
        f" FROM chunks WHERE {where} ORDER BY created_at DESC LIMIT 10",
        *params,
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
            "score": 0.5,
            "source": "metadata",
        }
        for row in rows
    ]
