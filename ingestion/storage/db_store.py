from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import TypedDict

from asyncpg import Pool

from shared.config.settings import settings


class EligibleFile(TypedDict):
    filename: str
    file_path: str
    sha256: str
    is_new: bool  # False = was rejected, needs reset


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def get_eligible_files(pdf_dir: str, pool: Pool) -> tuple[list[EligibleFile], list[str]]:
    """
    Scan pdf_dir for .pdf files.
    Returns (eligible, skipped_filenames).
    Eligible = new files + previously rejected files.
    Skipped = already ready or processing.
    """
    dir_path = Path(pdf_dir)
    pdfs = list(dir_path.glob("*.pdf"))

    if not pdfs:
        return [], []

    hashes = {_sha256(p): p for p in pdfs}

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
        elif status == "rejected":
            eligible.append({"filename": path.name, "file_path": str(path), "sha256": sha, "is_new": False})
        else:
            eligible.append({"filename": path.name, "file_path": str(path), "sha256": sha, "is_new": True})

    return eligible, skipped


async def create_document(filename: str, file_path: str, sha256: str, pool: Pool) -> uuid.UUID:
    row = await pool.fetchrow(
        """
        INSERT INTO documents (filename, file_path, sha256, status)
        VALUES ($1, $2, $3, 'pending')
        RETURNING id
        """,
        filename, file_path, sha256,
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
        """
        UPDATE documents
        SET status = $1,
            rejection_reason = $2,
            page_count = $3,
            processed_at = now()
        WHERE id = $4
        """,
        status, rejection_reason, page_count, document_id,
    )


async def insert_chunks(document_id: uuid.UUID, chunks: list[dict], pool: Pool) -> None:
    """
    Insert embedded chunks in a single transaction.
    Rolls back and raises on failure — caller should mark document rejected.
    Each chunk dict must have: text, embedding, metadata, section_path, page_start, page_end, token_count.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """
                INSERT INTO chunks
                    (document_id, text, embedding, metadata, section_path, page_start, page_end, token_count)
                VALUES ($1, $2, $3::vector, $4::jsonb, $5, $6, $7, $8)
                """,
                [
                    (
                        document_id,
                        c["text"],
                        str(c["embedding"]),
                        __import__("json").dumps(c["metadata"]),
                        c["section_path"],
                        c["page_start"],
                        c["page_end"],
                        c["token_count"],
                    )
                    for c in chunks
                ],
            )
