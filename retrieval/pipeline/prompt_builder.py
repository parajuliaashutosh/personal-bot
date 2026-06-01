from __future__ import annotations

_SYSTEM = (
    "You are a professional document assistant. "
    "Answer questions based ONLY on the provided context. "
    "If the answer is not in the context, say so clearly. "
    "Be concise and accurate. Never make up information."
)


def build_prompt(query: str, context: str) -> str:
    """Build the final prompt. History is passed separately to the LLM provider."""
    return (
        f"{_SYSTEM}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{query}\n\n"
        f"ANSWER:"
    )
