from __future__ import annotations

from retrieval.pipeline.merger import CandidateChunk
from retrieval.pipeline.query_understanding import QueryContext


def rank(candidates: list[CandidateChunk], context: QueryContext) -> list[CandidateChunk]:
    """Heuristic multi-signal scoring. Returns up to 50 candidates sorted best-first."""
    keywords = set(context.get("keywords", []))
    intent = context.get("intent", "general")

    scored: list[tuple[float, CandidateChunk]] = []
    for c in candidates:
        base = c["score"]

        # Boost chunks found by multiple searchers
        multi_source_bonus = 0.1 * (len(c["sources"]) - 1)

        # Keyword overlap with query
        chunk_words = set(c["text"].lower().split())
        keyword_overlap = len(keywords & chunk_words) / max(len(keywords), 1)
        keyword_bonus = keyword_overlap * 0.15

        # Quality score from metadata
        quality = float(c["metadata"].get("quality_score", 0.5))
        quality_bonus = quality * 0.1

        # Summary intent: prefer longer chunks
        length_bonus = 0.0
        if intent == "summary" and c["token_count"]:
            length_bonus = min(c["token_count"] / 800, 1.0) * 0.05

        # Penalise memory hits slightly (they're context, not direct answers)
        memory_penalty = -0.05 if c["sources"] == ["memory"] else 0.0

        final = base + multi_source_bonus + keyword_bonus + quality_bonus + length_bonus + memory_penalty
        scored.append((final, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    result = []
    for final_score, chunk in scored[:50]:
        chunk["score"] = round(final_score, 4)
        result.append(chunk)
    return result
