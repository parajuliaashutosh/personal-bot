from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator, Callable

from asyncpg import Pool

from ingestion.pipeline.chunker import chunk_sections
from ingestion.pipeline.cleaner import clean_pages
from ingestion.pipeline.embedder import embed_chunks
from ingestion.pipeline.enricher import enrich_chunks
from ingestion.pipeline.extractor import PageData, extract_pages
from ingestion.pipeline.filter import filter_chunks
from ingestion.pipeline.structure import detect_structure
from ingestion.pipeline.validator import validate_pdf
from ingestion.storage.db_store import (
    complete_ingest_run,
    create_document,
    create_ingest_run,
    get_eligible_files,
    insert_chunks,
    purge_all_documents,
    reset_document,
    update_document_status,
)


def _md_to_pages(text: str) -> list[PageData]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    blocks = []
    for para in paragraphs:
        first_line = para.splitlines()[0]
        if first_line.startswith("### "):
            font_size, text_val = 14.0, para[4:]
        elif first_line.startswith("## "):
            font_size, text_val = 16.0, para[3:]
        elif first_line.startswith("# "):
            font_size, text_val = 18.0, para[2:]
        else:
            font_size, text_val = 12.0, para
        blocks.append({
            "text": text_val,
            "font_size": font_size,
            "bbox": (0.0, 0.0, 0.0, 0.0),
            "block_type": "text",
        })
    return [{"page_number": 1, "blocks": blocks}]


def _extract_pages(file_path: str) -> list[PageData]:
    if file_path.endswith(".md"):
        return _md_to_pages(Path(file_path).read_text(encoding="utf-8", errors="replace"))
    return clean_pages(extract_pages(file_path))


async def process_files(files: list[dict], pool: Pool, embed_fn: Callable) -> AsyncIterator[str]:
    """Process a list of eligible files through the full ingestion pipeline. Yields SSE-ready JSON."""
    for file in files:

        # Step 1: Validate — reject corrupt/oversized PDFs before any DB writes
        yield json.dumps({"stage": "validating", "file": file["filename"]})
        is_pdf = file["file_path"].endswith(".pdf")

        try:
            if is_pdf:
                _, err = await validate_pdf(file["file_path"])
                if err:
                    doc_id = (
                        await create_document(file["filename"], file["file_path"], file["sha256"], pool)
                        if file["is_new"]
                        else await reset_document(file["sha256"], pool)
                    )
                    await update_document_status(doc_id, "failed", pool, rejection_reason=err.code)
                    yield json.dumps({"stage": "failed", "file": file["filename"], "error": err.code})
                    continue

            # Step 2: Register document in DB and mark as processing
            doc_id = (
                await create_document(file["filename"], file["file_path"], file["sha256"], pool)
                if file["is_new"]
                else await reset_document(file["sha256"], pool)
            )
            await update_document_status(doc_id, "processing", pool)

            # Step 3: Extract text and detect document structure
            yield json.dumps({"stage": "extracting", "file": file["filename"]})
            pages = _extract_pages(file["file_path"])
            sections = detect_structure(pages)

            # Step 4: Chunk, enrich with metadata, filter low-quality chunks
            raw_chunks = chunk_sections(sections)
            enriched = enrich_chunks(raw_chunks, doc_id)
            filtered = filter_chunks(enriched)

            # Step 5: Embed chunks and persist to DB
            yield json.dumps({"stage": "embedding", "file": file["filename"]})
            embedded = await embed_chunks(filtered, embed_fn)
            await insert_chunks(doc_id, embedded, pool)
            await update_document_status(doc_id, "ready", pool, page_count=len(pages))

            yield json.dumps({"stage": "done", "file": file["filename"], "chunks": len(embedded)})

        except Exception as exc:
            yield json.dumps({"stage": "failed", "file": file["filename"], "error": str(exc)})


async def reprocess_stream(
    pdf_dir: str,
    pool: Pool,
    embed_fn: Callable,
) -> AsyncIterator[str]:
    """Purge all docs/chunks, open an audit run, re-ingest everything. Yields SSE-ready JSON strings."""

    # Step 1: Snapshot file list from disk before purge
    all_files_on_disk = [
        p.name for p in Path(pdf_dir).glob("*") if p.suffix in (".pdf", ".md")
    ]

    # Step 2: Purge all existing documents and chunks
    prev_docs, prev_chunks = await purge_all_documents(pool)
    yield json.dumps({"stage": "purged", "prev_docs": prev_docs, "prev_chunks": prev_chunks})

    # Step 3: Open audit run record
    run_id = await create_ingest_run(all_files_on_disk, pool)

    # Step 4: Re-scan eligible files (all new after purge)
    eligible, _ = await get_eligible_files(pdf_dir, pool)

    # Step 5: Process each file and stream progress
    total_docs = 0
    total_chunks = 0
    error: str | None = None

    try:
        async for raw in process_files(eligible, pool, embed_fn):
            event = json.loads(raw)
            if event.get("stage") == "done":
                total_docs += 1
                total_chunks += event.get("chunks", 0)
            yield raw
    except Exception as exc:
        error = str(exc)
        yield json.dumps({"stage": "error", "error": error})
    finally:
        # Step 6: Close audit run with final counts
        await complete_ingest_run(run_id, pool, total_docs, total_chunks, error)
        yield json.dumps({
            "stage": "finished",
            "run_id": str(run_id),
            "docs": total_docs,
            "chunks": total_chunks,
        })
