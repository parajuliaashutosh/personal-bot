from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator, Callable

from retrieval.pipeline.merger import CandidateChunk
from retrieval.pipeline.query_understanding import QueryContext
from shared.config.settings import settings

logger = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\[.*?\]", re.DOTALL)
_WORD_RE = re.compile(r"[a-z0-9]+")
_TOP_N = 12




async def _collect(stream: AsyncIterator[str]) -> str:
    parts: list[str] = []
    async for token in stream:
        parts.append(token)
    return "".join(parts)


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _phrase_bonus(query: str, text: str) -> float:
    """Reward the longest contiguous query phrase that appears verbatim."""
    words = _WORD_RE.findall(query.lower())
    lowered = text.lower()
    for size in range(min(len(words), 6), 1, -1):
        for start in range(len(words) - size + 1):
            if " ".join(words[start:start + size]) in lowered:
                return min(size / 6, 1.0)
    return 0.0


def rerank_local(
    query: str,
    candidates: list[CandidateChunk],
    context: QueryContext | None = None,
    top_n: int = _TOP_N,
) -> list[CandidateChunk]:
    """Relevance + diversity rerank with no model call.

    Two signals the upstream `rank()` pass cannot see:
      * verbatim phrase matches, which separate a chunk that actually discusses
        the question from one that merely shares vocabulary with it;
      * redundancy — vector search happily returns six near-identical chunks
        from the same section, crowding out the passage that answers the rest
        of the question. MMR keeps the best of a cluster and moves on.
    """
    if not candidates:
        return []

    query_tokens = _tokens(query)
    entities = {e.lower() for e in (context or {}).get("entities", [])}

    scored: list[tuple[float, set[str], CandidateChunk]] = []
    for c in candidates:
        chunk_tokens = _tokens(c["text"])
        coverage = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
        entity_hit = len(entities & chunk_tokens) / max(len(entities), 1) if entities else 0.0

        relevance = (
            c["score"]
            + 0.25 * _phrase_bonus(query, c["text"])
            + 0.15 * coverage
            + 0.10 * entity_hit
        )
        scored.append((relevance, chunk_tokens, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Normalise relevance to 0..1 so it is comparable with the redundancy term;
    # raw scores span a narrow band and would otherwise always outvote MMR.
    top = scored[0][0]
    bottom = scored[-1][0]
    span = (top - bottom) or 1.0

    selected: list[CandidateChunk] = []
    selected_tokens: list[set[str]] = []
    pool = scored[:]

    while pool and len(selected) < top_n:
        best_i = 0
        best_score = float("-inf")
        lam = settings.rerank_relevance_weight
        for i, (relevance, chunk_tokens, _) in enumerate(pool):
            redundancy = max((_jaccard(chunk_tokens, s) for s in selected_tokens), default=0.0)
            normalised = (relevance - bottom) / span
            mmr = lam * normalised - (1 - lam) * redundancy
            if mmr > best_score:
                best_score, best_i = mmr, i

        relevance, chunk_tokens, chunk = pool.pop(best_i)
        chunk["score"] = round(relevance, 4)
        selected.append(chunk)
        selected_tokens.append(chunk_tokens)

    return selected


async def rerank(
    query: str,
    candidates: list[CandidateChunk],
    llm_fn: Callable[[str, list[dict[str, str]]], AsyncIterator[str]],
    context: QueryContext | None = None,
) -> list[CandidateChunk]:
    """Pick the best passages to put in the prompt.

    Local by default: scoring 20 passages with the model costs a second generate
    call per chat, which is the first thing to blow a free-tier quota. Set
    LLM_RERANK=true to use the model; it falls back to the local rerank on any
    failure.
    """
    if not candidates:
        return []

    if len(candidates) <= _TOP_N:
        return candidates

    if not settings.llm_rerank:
        return rerank_local(query, candidates, context)

    snippets = "\n\n".join(
        f"[{i}] {c['text'][:300]}"
        for i, c in enumerate(candidates)
    )
    prompt = (
        f"Question: {query}\n\n"
        f"Rate the relevance of each passage (0–10, 10=most relevant):\n\n"
        f"{snippets}\n\n"
        f"Respond with a JSON array only, no explanation:\n"
        f'[{{"index": 0, "score": 8}}, {{"index": 1, "score": 3}}, ...]'
    )

    try:
        raw = await _collect(llm_fn(prompt, []))
        match = _JSON_RE.search(raw)
        if not match:
            raise ValueError("no JSON array in response")

        scores: list[dict] = json.loads(match.group())
        index_to_score = {int(s["index"]): float(s["score"]) for s in scores}

        for i, c in enumerate(candidates):
            if i in index_to_score:
                c["score"] = index_to_score[i] / 10.0

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates[:_TOP_N]
    except Exception as exc:
        logger.warning("LLM rerank failed (%s), using local rerank", exc)
        return rerank_local(query, candidates, context)
