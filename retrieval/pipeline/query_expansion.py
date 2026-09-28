from __future__ import annotations

import logging
import re
from typing import AsyncIterator, Callable

from retrieval.pipeline.query_understanding import QueryContext
from shared.config.settings import settings

logger = logging.getLogger(__name__)

_MAX_VARIATIONS = 2

_FILLER_RE = re.compile(
    r"\b(can you|could you|please|tell me about|tell me|explain|describe|"
    r"give me|show me|i want to know|what about|how about|do you know)\b",
    re.I,
)

_INTENT_HINTS = {
    "summary": "overview summary",
    "comparison": "comparison difference between",
    "factual": "",
    "general": "",
}


async def _collect(stream: AsyncIterator[str]) -> str:
    parts: list[str] = []
    async for token in stream:
        parts.append(token)
    return "".join(parts)


def _dedupe(query: str, candidates: list[str]) -> list[str]:
    seen = {query.strip().lower()}
    out: list[str] = []
    for c in candidates:
        c = c.strip()
        key = c.lower()
        if not c or key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out[:_MAX_VARIATIONS]


def expand_query_local(query: str, context: QueryContext) -> list[str]:
    """Build search variations with no model call.

    Conversational queries ("can you tell me about your GitOps setup?") embed
    poorly against document prose. Stripping the filler and re-stating the query
    as its keywords and entities gives the vector search a second, denser probe
    for free.
    """
    keywords = context.get("keywords", [])
    entities = context.get("entities", [])
    intent = context.get("intent", "general")

    variations: list[str] = []

    stripped = _FILLER_RE.sub(" ", query)
    stripped = re.sub(r"[?!.]+", " ", stripped)
    stripped = " ".join(stripped.split())
    if stripped:
        variations.append(stripped)

    if keywords:
        hint = _INTENT_HINTS.get(intent, "")
        dense = " ".join(dict.fromkeys([*entities, *keywords]))
        variations.append(f"{dense} {hint}".strip())

    return _dedupe(query, variations)


async def expand_query(
    query: str,
    context: QueryContext,
    llm_fn: Callable[[str, list[dict[str, str]]], AsyncIterator[str]],
) -> list[str]:
    """Alternative phrasings to widen vector recall.

    Local by default — an LLM round trip here would double the generate calls
    per chat for a marginal gain. Set LLM_QUERY_EXPANSION=true to use the model
    instead; it falls back to the local variations if the call fails.
    """
    if not settings.llm_query_expansion:
        return expand_query_local(query, context)

    prompt = (
        "Generate 2 alternative search phrasings for the query below. "
        "Return only the alternatives, one per line, no numbering, no explanation.\n\n"
        f"Query: {query}"
    )
    try:
        raw = await _collect(llm_fn(prompt, []))
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        expanded = _dedupe(query, lines)
        return expanded or expand_query_local(query, context)
    except Exception as exc:
        logger.warning("LLM query expansion failed (%s), using local variations", exc)
        return expand_query_local(query, context)
