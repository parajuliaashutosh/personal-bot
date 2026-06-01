from __future__ import annotations

import uuid
from typing import TypedDict


class CandidateChunk(TypedDict):
    id: uuid.UUID
    document_id: uuid.UUID
    text: str
    section_path: list[str]
    page_start: int | None
    page_end: int | None
    token_count: int | None
    metadata: dict
    score: float
    sources: list[str]


def merge(results: list[dict]) -> list[CandidateChunk]:
    """Deduplicate by chunk id, keep highest score, merge source labels."""
    seen: dict[uuid.UUID, CandidateChunk] = {}

    for r in results:
        chunk_id: uuid.UUID = r["id"]
        source: str = r.get("source", "unknown")
        score: float = float(r.get("score", 0.0))

        if chunk_id in seen:
            existing = seen[chunk_id]
            if score > existing["score"]:
                existing["score"] = score
            if source not in existing["sources"]:
                existing["sources"].append(source)
        else:
            seen[chunk_id] = {
                "id": chunk_id,
                "document_id": r["document_id"],
                "text": r["text"],
                "section_path": r.get("section_path", []),
                "page_start": r.get("page_start"),
                "page_end": r.get("page_end"),
                "token_count": r.get("token_count"),
                "metadata": r.get("metadata", {}),
                "score": score,
                "sources": [source],
            }

    return list(seen.values())
