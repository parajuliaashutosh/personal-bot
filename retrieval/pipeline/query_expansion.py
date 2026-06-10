from __future__ import annotations

from typing import AsyncIterator, Callable

from retrieval.pipeline.query_understanding import QueryContext


async def _collect(stream: AsyncIterator[str]) -> str:
    parts: list[str] = []
    async for token in stream:
        parts.append(token)
    return "".join(parts)


async def expand_query(
    query: str,
    context: QueryContext,
    llm_fn: Callable[[str, list[dict[str, str]]], AsyncIterator[str]],
) -> list[str]:
    prompt = (
        "Generate 2 alternative search phrasings for the query below. "
        "Return only the alternatives, one per line, no numbering, no explanation.\n\n"
        f"Query: {query}"
    )
    try:
        raw = await _collect(await llm_fn(prompt, []))
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return [ln for ln in lines if ln.lower() != query.lower()][:2]
    except Exception:
        return []
