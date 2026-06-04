from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ingestion.pipeline.chunker import chunk_sections
from ingestion.pipeline.cleaner import clean_pages
from ingestion.pipeline.embedder import embed_chunks
from ingestion.pipeline.enricher import enrich_chunks
from ingestion.pipeline.extractor import PageData, extract_pages
from ingestion.pipeline.filter import filter_chunks
from ingestion.pipeline.structure import detect_structure
from ingestion.pipeline.validator import validate_pdf
from ingestion.storage.db_store import (
    create_document,
    get_eligible_files,
    insert_chunks,
    list_documents,
    reset_document,
    update_document_status,
)
from shared.config.settings import settings

router = APIRouter(prefix="/ingest", tags=["ingest"])


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


def _extract_pages_for_file(file_path: str) -> list[PageData]:
    if file_path.endswith(".md"):
        return _md_to_pages(Path(file_path).read_text(encoding="utf-8", errors="replace"))
    pages = extract_pages(file_path)
    return clean_pages(pages)


async def _process_files(files: list[dict], pool, embed_fn):
    for file in files:
        yield json.dumps({"stage": "validating", "file": file["filename"]})
        is_pdf = file["file_path"].endswith(".pdf")

        try:
            if is_pdf:
                ok, err = await validate_pdf(file["file_path"])
                if err:
                    doc_id = (
                        await create_document(file["filename"], file["file_path"], file["sha256"], pool)
                        if file["is_new"]
                        else await reset_document(file["sha256"], pool)
                    )
                    await update_document_status(doc_id, "failed", pool, rejection_reason=err.code)
                    yield json.dumps({"stage": "failed", "file": file["filename"], "error": err.code})
                    continue

            doc_id = (
                await create_document(file["filename"], file["file_path"], file["sha256"], pool)
                if file["is_new"]
                else await reset_document(file["sha256"], pool)
            )
            await update_document_status(doc_id, "processing", pool)

            yield json.dumps({"stage": "extracting", "file": file["filename"]})
            pages = _extract_pages_for_file(file["file_path"])
            sections = detect_structure(pages)
            raw_chunks = chunk_sections(sections)
            enriched = enrich_chunks(raw_chunks, doc_id)
            filtered = filter_chunks(enriched)

            yield json.dumps({"stage": "embedding", "file": file["filename"]})
            embedded = await embed_chunks(filtered, embed_fn)

            await insert_chunks(doc_id, embedded, pool)
            await update_document_status(doc_id, "ready", pool, page_count=len(pages))
            yield json.dumps({"stage": "done", "file": file["filename"], "chunks": len(embedded)})

        except Exception as exc:
            yield json.dumps({"stage": "failed", "file": file["filename"], "error": str(exc)})


@router.post("/process")
async def process_all(request: Request):
    pool = request.app.state.pool
    embed_fn = request.app.state.embed_fn
    eligible, skipped = await get_eligible_files(settings.pdf_dir, pool)

    if not eligible:
        return {"queued": [], "skipped": skipped, "failed": []}

    async def generate():
        async for event in _process_files(eligible, pool, embed_fn):
            yield event

    return EventSourceResponse(generate())


@router.post("/process/{filename}")
async def process_one(filename: str, request: Request):
    pool = request.app.state.pool
    embed_fn = request.app.state.embed_fn
    eligible, skipped = await get_eligible_files(settings.pdf_dir, pool)

    target = next((f for f in eligible if f["filename"] == filename), None)
    if target is None:
        if filename in skipped:
            raise HTTPException(status_code=409, detail={
                "code": "ALREADY_PROCESSED", "message": f"{filename} is already ready or processing"})
        raise HTTPException(status_code=404, detail={
            "code": "FILE_NOT_FOUND", "message": f"{filename} not found or not eligible"})

    async def generate():
        async for event in _process_files([target], pool, embed_fn):
            yield event

    return EventSourceResponse(generate())


@router.get("/documents")
async def get_documents(request: Request):
    pool = request.app.state.pool
    return await list_documents(pool)
