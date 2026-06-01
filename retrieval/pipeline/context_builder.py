from __future__ import annotations

from retrieval.pipeline.merger import CandidateChunk

_CHARS_PER_TOKEN = 4


def build_context(chunks: list[CandidateChunk], token_limit: int) -> str:
    """Group chunks by section, pack into context string within token limit."""
    char_limit = token_limit * _CHARS_PER_TOKEN
    used = 0
    sections: dict[str, list[str]] = {}

    for chunk in chunks:
        path = " > ".join(chunk["section_path"]) if chunk["section_path"] else "General"
        if path not in sections:
            sections[path] = []
        sections[path].append(chunk["text"])

    parts: list[str] = []

    for section_path, texts in sections.items():
        header = f"[{section_path}]"
        body = "\n\n".join(texts)
        block = f"{header}\n{body}"
        block_len = len(block)

        if used + block_len > char_limit:
            remaining = char_limit - used
            if remaining > len(header) + 50:
                truncated = block[:remaining].rsplit(" ", 1)[0]
                parts.append(truncated)
            break

        parts.append(block)
        used += block_len + 2  # +2 for separator

    return "\n\n".join(parts)
