from __future__ import annotations

import re
from typing import TypedDict


class PostprocessResult(TypedDict):
    answer: str
    is_grounded: bool
    confidence: str  # "high" | "medium" | "low"


_LOW_CONFIDENCE_RE = re.compile(
    r"\b(i (don't|do not|cannot|can't) (find|know|see|locate)|"
    r"not (found|mentioned|available|in the (context|document))|"
    r"no information|unclear|not sure|uncertain)\b",
    re.I,
)


def postprocess(answer: str, context: str) -> PostprocessResult:
    if _LOW_CONFIDENCE_RE.search(answer):
        return {"answer": answer, "is_grounded": False, "confidence": "low"}

    # Check rough grounding: at least one 4+ word phrase from answer appears in context
    answer_phrases = re.findall(r"\b\w+(?: \w+){3,}\b", answer)
    is_grounded = any(phrase.lower() in context.lower() for phrase in answer_phrases[:10])

    confidence = "high" if is_grounded else "medium"
    return {"answer": answer, "is_grounded": is_grounded, "confidence": confidence}
