from __future__ import annotations

from typing import AsyncIterator, Callable

_PROMPT = """\
You are given full text extracted from one person's documents (CV, bio, project write-ups, etc.).
Extract a minimal identity card for that person — this will be injected into every chat prompt as
context, so keep it very short (3 lines max).

Include ONLY:
1. Full name
2. Role / designation (current title or most recent job title, years of experience if derivable)
3. Contact (email, phone number, LinkedIn, GitHub — one line)

Rules:
- Use ONLY information present in the source text. Never invent facts.
- Plain text only — no markdown, no bullet points, no extra sections.
- Output only the three lines, no preamble or commentary.

SOURCE DOCUMENTS:
{corpus}
"""


async def _collect(stream: AsyncIterator[str]) -> str:
    parts: list[str] = []
    async for token in stream:
        parts.append(token)
    return "".join(parts)


async def build_persona(
    corpus_text: str,
    generate_fn: Callable[[str, list[dict[str, str]]], AsyncIterator[str]],
) -> str:
    """Infer the person's profile from the ingested corpus using the LLM."""
    if not corpus_text.strip():
        return ""
    prompt = _PROMPT.format(corpus=corpus_text)
    return (await _collect(generate_fn(prompt, []))).strip()
