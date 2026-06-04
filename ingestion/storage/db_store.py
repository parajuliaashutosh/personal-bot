from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import TypedDict

from asyncpg import Pool


class EligibleFile(TypedDict):
    filename: str
    file_path: str
    sha256: str
    is_new: bool  # False = was rejected/failed, needs reset


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def get_eligible_files(
    pdf_dir: str, pool: Pool
) -> tuple[list[EligibleFile], list[str]]:
    dir_path = Path(pdf_dir)
    files = list(dir_path.glob("*.pdf")) + list(dir_path.glob("*.md"))

    if not files:
        return [], []

    hashes = {_sha256(p): p for p in files}
    rows = await pool.fetch(
        "SELECT sha256, status FROM documents WHERE sha256 = ANY($1::text[])",
        list(hashes.keys()),
    )
    known = {r["sha256"]: r["status"] for r in rows}

    eligible: list[EligibleFile] = []
    skipped: list[str] = []

    for sha, path in hashes.items():
        status = known.get(sha)
        if status in ("ready", "processing"):
            skipped.append(path.name)
        elif status in ("rejected", "failed"):
            eligible.append({"filename": path.name, "file_path": str(path), "sha256": sha, "is_new": False})
        else:
            eligible.append({"filename": path.name, "file_path": str(path), "sha256": sha, "is_new": True})

    return eligible, skipped


async def create_document(
    filename: str, file_path: str, sha256: str, pool: Pool
) -> uuid.UUID:
    row = await pool.fetchrow(
        "INSERT INTO documents (filename, file_path, sha256, status)"
        " VALUES ($1, $2, $3, 'pending') RETURNING id",
        filename, file_path, sha256,
    )
    return row["id"]


async def reset_document(sha256: str, pool: Pool) -> uuid.UUID:
    row = await pool.fetchrow(
        "UPDATE documents"
        " SET status = 'pending', rejection_reason = NULL, processed_at = now()"
        " WHERE sha256 = $1 RETURNING id",
        sha256,
    )
    return row["id"]


async def update_document_status(
    document_id: uuid.UUID,
    status: str,
    pool: Pool,
    rejection_reason: str | None = None,
    page_count: int | None = None,
) -> None:
    await pool.execute(
        "UPDATE documents"
        " SET status = $1,"
        "     rejection_reason = COALESCE($2, rejection_reason),"
        "     page_count = COALESCE($3, page_count),"
        "     processed_at = now()"
        " WHERE id = $4",
        status, rejection_reason, page_count, document_id,
    )


async def insert_chunks(
    document_id: uuid.UUID, chunks: list[dict], pool: Pool
) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            for c in chunks:
                embedding_str = "[" + ",".join(str(x) for x in c["embedding"]) + "]"
                metadata = json.dumps({
                    "keywords": c.get("keywords", []),
                    "language": c.get("language", "en"),
                    "quality_score": c.get("quality_score", 0.0),
                })
                await conn.execute(
                    "INSERT INTO chunks"
                    " (document_id, text, embedding, metadata, section_path,"
                    "  page_start, page_end, token_count)"
                    " VALUES ($1, $2, $3::vector, $4::jsonb, $5, $6, $7, $8)",
                    document_id,
                    c["text"],
                    embedding_str,
                    metadata,
                    c.get("section_path", []),
                    c.get("page_start"),
                    c.get("page_end"),
                    c.get("token_count"),
                )


async def delete_document_by_sha256(sha256: str, pool: Pool) -> None:
    await pool.execute("DELETE FROM documents WHERE sha256 = $1", sha256)


async def get_document_by_id(document_id: uuid.UUID, pool: Pool) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM documents WHERE id = $1", document_id)
    return dict(row) if row else None


async def list_documents(pool: Pool) -> list[dict]:
    rows = await pool.fetch("SELECT * FROM documents ORDER BY processed_at DESC")
    return [dict(r) for r in rows]
