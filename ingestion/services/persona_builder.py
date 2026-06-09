from __future__ import annotations

from typing import AsyncIterator, Callable

_PROMPT = """\
You are given the full text extracted from one person's documents (CV, bio, project
write-ups, etc.). Write a concise factual profile of THAT person, to be used as the
"about this person" reference for a portfolio assistant.

Rules:
- Use ONLY information present in the source text. Never invent facts.
- Capture: full name, contact links (LinkedIn, GitHub, email, phone, site), a short
  introduction, key skills, work experience (roles, companies, dates), and notable
  projects with any URLs.
- Keep it well-structured and readable (markdown headings/bullets are fine).
- Output only the profile — no preamble, no commentary.

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
    return (await _collect(await generate_fn(prompt, []))).strip()
