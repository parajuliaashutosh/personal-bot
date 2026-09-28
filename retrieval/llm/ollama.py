from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from retrieval.llm.guards import StreamCutShort
from shared.config.settings import settings

_client = httpx.AsyncClient(timeout=120.0)
_embed_client = httpx.AsyncClient(timeout=60.0)


async def generate(
    prompt: str,
    history: list[dict[str, str]],
) -> AsyncIterator[str]:
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": prompt})

    async with _client.stream(
        "POST",
        f"{settings.ollama_base_url}/api/chat",
        json={"model": settings.ollama_model, "messages": messages, "stream": True},
    ) as resp:
        resp.raise_for_status()
        done_reason: str | None = None
        saw_done = False

        async for line in resp.aiter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue

            if err := chunk.get("error"):
                raise RuntimeError(f"ollama stream error: {err}")

            if token := chunk.get("message", {}).get("content", ""):
                yield token

            if chunk.get("done"):
                saw_done = True
                done_reason = chunk.get("done_reason")
                break

        if saw_done and done_reason and done_reason != "stop":
            raise StreamCutShort("ollama", done_reason)
        if not saw_done:
            raise StreamCutShort("ollama", "connection_closed")


async def embed(texts: list[str]) -> list[list[float]]:
    results: list[list[float]] = []
    for text in texts:
        resp = await _embed_client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        resp.raise_for_status()
        results.append(resp.json()["embedding"])
    return results
