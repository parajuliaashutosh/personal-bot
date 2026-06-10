from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ingestion.services.ingest_service import process_files, reprocess_stream
from ingestion.storage.db_store import get_eligible_files, list_documents, list_ingest_runs
from shared.config.settings import settings

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/process")
async def process_all(request: Request):
    pool = request.app.state.pool
    embed_fn = request.app.state.embed_fn
    eligible, skipped = await get_eligible_files(settings.data_dir, pool)

    if not eligible:
        return {"queued": [], "skipped": skipped, "failed": []}

    async def generate():
        async for event in process_files(eligible, pool, embed_fn):
            yield event

    return EventSourceResponse(generate())


@router.post("/process/{filename}")
async def process_one(filename: str, request: Request):
    pool = request.app.state.pool
    embed_fn = request.app.state.embed_fn
    eligible, skipped = await get_eligible_files(settings.data_dir, pool)

    target = next((f for f in eligible if f["filename"] == filename), None)
    if target is None:
        if filename in skipped:
            raise HTTPException(status_code=409, detail={
                "code": "ALREADY_PROCESSED",
                "message": f"{filename} is already ready or processing",
            })
        raise HTTPException(status_code=404, detail={
            "code": "FILE_NOT_FOUND",
            "message": f"{filename} not found or not eligible",
        })

    async def generate():
        async for event in process_files([target], pool, embed_fn):
            yield event

    return EventSourceResponse(generate())


@router.post("/reprocess")
async def reprocess_all(request: Request):
    pool = request.app.state.pool
    embed_fn = request.app.state.embed_fn
    generate_fn = request.app.state.generate_fn

    async def generate():
        async for event in reprocess_stream(settings.data_dir, pool, embed_fn, generate_fn):
            yield event

    return EventSourceResponse(generate())


@router.get("/documents")
async def get_documents(request: Request):
    pool = request.app.state.pool
    return await list_documents(pool)


@router.get("/runs")
async def get_ingest_runs(request: Request):
    pool = request.app.state.pool
    return await list_ingest_runs(pool)
