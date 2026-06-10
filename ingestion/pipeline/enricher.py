from __future__ import annotations

import re
import uuid
from collections import Counter
from typing import TypedDict

from ingestion.pipeline.chunker import RawChunk


class EnrichedChunk(TypedDict):
    text: str
    section_path: list[str]
    page_start: int
    page_end: int
    document_id: uuid.UUID
    keywords: list[str]
    language: str
    token_count: int
    quality_score: float


_STOP = frozenset(
    "the a an and or but in on at to for of with by from as is are was were be been "
    "being have has had do does did will would could should may might must can this "
    "that these those all some more most other such only own same so than too very "
    "just it its we our they their i my you your he she his her".split()
)

_WORD_RE = re.compile(r"\b[a-zA-Z]{3,}\b")


def _keywords(text: str, n: int = 8) -> list[str]:
    words = [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOP]
    return [w for w, _ in Counter(words).most_common(n)]


def _language(text: str) -> str:
    """Cheap heuristic: count ASCII letters vs non-ASCII."""
    sample = text[:500]
    non_ascii = sum(1 for c in sample if ord(c) > 127)
    return "en" if non_ascii / max(len(sample), 1) < 0.15 else "other"


def _quality_score(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0

    avg_word_len = sum(len(w) for w in words) / len(words)
    word_len_score = min(avg_word_len / 6.0, 1.0)  # ideal ~6 chars

    punct = sum(1 for c in text if c in ".,:;!?")
    punct_score = min(punct / max(len(words), 1), 1.0)

    digits = sum(1 for c in text if c.isdigit())
    digit_ratio = digits / max(len(text), 1)
    digit_penalty = max(0.0, 1.0 - digit_ratio * 2)

    return round((word_len_score * 0.5 + punct_score * 0.3 + digit_penalty * 0.2), 3)


def enrich_chunks(chunks: list[RawChunk], document_id: uuid.UUID) -> list[EnrichedChunk]:
    enriched: list[EnrichedChunk] = []
    for c in chunks:
        enriched.append({
            "text": c["text"],
            "section_path": c["section_path"],
            "page_start": c["page_start"],
            "page_end": c["page_end"],
            "document_id": document_id,
            "keywords": _keywords(c["text"]),
            "language": _language(c["text"]),
            "token_count": len(c["text"]) // 4,
            "quality_score": _quality_score(c["text"]),
        })
    return enriched
