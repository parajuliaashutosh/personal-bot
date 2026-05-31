from __future__ import annotations

import hashlib
import unicodedata

from ingestion.pipeline.enricher import EnrichedChunk


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower().split()  # type: ignore[return-value]


def _sha256(text: str) -> str:
    normalized = " ".join(_normalize(text))  # type: ignore[arg-type]
    return hashlib.sha256(normalized.encode()).hexdigest()


def _digit_symbol_ratio(text: str) -> float:
    if not text:
        return 1.0
    count = sum(1 for c in text if c.isdigit() or not c.isalnum())
    return count / len(text)


def filter_chunks(chunks: list[EnrichedChunk]) -> list[EnrichedChunk]:
    seen: set[str] = set()
    result: list[EnrichedChunk] = []

    for chunk in chunks:
        text = chunk["text"]

        if len(text) < 50:
            continue
        if chunk["quality_score"] < 0.3:
            continue
        if _digit_symbol_ratio(text) > 0.5:
            continue

        h = _sha256(text)
        if h in seen:
            continue

        seen.add(h)
        result.append(chunk)

    return result
