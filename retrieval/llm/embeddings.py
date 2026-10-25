from __future__ import annotations

import httpx

from shared.config.settings import settings

_client = httpx.AsyncClient(timeout=60.0)


async def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    resp = await _client.post(
        f"{settings.embed_base_url}/embeddings",
        headers={
            "Authorization": f"Bearer {settings.embed_api_key or settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.embed_model,
            "input": texts,
            "dimensions": settings.embed_dimensions,
        },
    )
    resp.raise_for_status()
    body = resp.json()
    if err := body.get("error"):
        raise RuntimeError(f"embedding error: {err.get('message', err)}")

    rows = sorted(body["data"], key=lambda r: r["index"])
    vectors = [r["embedding"] for r in rows]
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"embedding count mismatch: sent {len(texts)}, got {len(vectors)}")
    if vectors and len(vectors[0]) != settings.embed_dimensions:
        raise RuntimeError(
            f"embedding has {len(vectors[0])} dims, DB expects "
            f"{settings.embed_dimensions} — check EMBED_MODEL / EMBED_DIMENSIONS"
        )
    return vectors
