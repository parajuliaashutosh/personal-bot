from __future__ import annotations

from typing import Awaitable, Callable, TypedDict

from ingestion.pipeline.enricher import EnrichedChunk
from shared.config.settings import settings


class EmbeddedChunk(TypedDict):
    text: str
    section_path: list[str]
    page_start: int
    page_end: int
    document_id: object  # uuid.UUID
    keywords: list[str]
    language: str
    token_count: int
    quality_score: float
    embedding: list[float]


async def embed_chunks(
    chunks: list[EnrichedChunk],
    embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
) -> list[EmbeddedChunk]:
    results: list[EmbeddedChunk] = []
    batch_size = settings.embed_batch_size

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = await embed_fn(texts)

        for chunk, embedding in zip(batch, embeddings):
            results.append({**chunk, "embedding": embedding})  # type: ignore[typeddict-item]

    return results
