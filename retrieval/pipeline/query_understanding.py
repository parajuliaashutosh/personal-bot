from __future__ import annotations

import re
from typing import TypedDict

from shared.errors import AppError


class QueryContext(TypedDict):
    language: str
    intent: str  # "factual" | "summary" | "comparison" | "general"
    entities: list[str]
    keywords: list[str]


_SUMMARY_RE = re.compile(r"\b(summar|overview|brief|tldr|outline|recap)\w*\b", re.I)
_COMPARISON_RE = re.compile(r"\b(compar|vs|versus|differ|contrast|between)\w*\b", re.I)
_FACTUAL_RE = re.compile(r"\b(what|who|when|where|which|how many|how much|define|list)\b", re.I)
_WORD_RE = re.compile(r"\b[a-zA-Z]{3,}\b")
_ENTITY_RE = re.compile(r"(?<!\.\s)(?<!\A)(?<!\n)[A-Z][a-z]{2,}")

_STOP = frozenset(
    "the a an and or but in on at to for of with by from as is are was were be been "
    "being have has had do does did will would could should may might must can this "
    "that these those all some more most other such only own same so than too very "
    "just it its we our they their i my you your he she his her tell explain describe "
    "give find show me please".split()
)


async def understand_query(query: str) -> tuple[QueryContext | None, AppError | None]:
    words = [w.lower() for w in _WORD_RE.findall(query)]
    keywords = [w for w in words if w not in _STOP]

    if _SUMMARY_RE.search(query):
        intent = "summary"
    elif _COMPARISON_RE.search(query):
        intent = "comparison"
    elif _FACTUAL_RE.search(query):
        intent = "factual"
    else:
        intent = "general"

    entities = list({m.group() for m in _ENTITY_RE.finditer(query)})

    ctx: QueryContext = {
        "language": "en",
        "intent": intent,
        "entities": entities,
        "keywords": keywords[:15],
    }
    return ctx, None
