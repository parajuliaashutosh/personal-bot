from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator, Callable

from retrieval.pipeline.merger import CandidateChunk

logger = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\[.*?\]", re.DOTALL)
_TOP_N = 12


async def _collect(stream: AsyncIterator[str]) -> str:
    parts: list[str] = []
    async for token in stream:
        parts.append(token)
    return "".join(parts)


async def rerank(
    query: str,
    candidates: list[CandidateChunk],
    llm_fn: Callable[[str, list[dict[str, str]]], AsyncIterator[str]],
) -> list[CandidateChunk]:
    if not candidates:
        return []

    if len(candidates) <= _TOP_N:
        return candidates

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
        raw = await _collect(await llm_fn(prompt, []))
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
        logger.warning("reranker failed, using heuristic order: %s", exc)
        return candidates[:_TOP_N]
