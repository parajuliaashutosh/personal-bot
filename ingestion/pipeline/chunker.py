from __future__ import annotations

from typing import TypedDict

from ingestion.pipeline.structure import SectionNode

_TARGET_MIN = 300 * 4   # chars (~300 tokens)
_TARGET_MAX = 800 * 4   # chars (~800 tokens)
_OVERLAP = 75 * 4       # chars (~75 tokens)


class RawChunk(TypedDict):
    text: str
    section_path: list[str]
    page_start: int
    page_end: int


def chunk_sections(sections: list[SectionNode]) -> list[RawChunk]:
    chunks: list[RawChunk] = []
    _walk(sections, path=[], chunks=chunks, prev_tail="")
    return chunks


def _walk(
    nodes: list[SectionNode],
    path: list[str],
    chunks: list[RawChunk],
    prev_tail: str,
) -> str:
    """Recursively walk section tree, return last tail text for overlap."""
    for node in nodes:
        current_path = path + ([node["title"]] if node["title"] else [])

        # Collect body text for this node
        body_blocks = node["blocks"]
        body_text = "\n\n".join(b["text"] for b in body_blocks).strip()
        page_start = body_blocks[0]["bbox"][1] if body_blocks else 0  # use block y as proxy
        # page numbers come from the section node itself
        pnum = node["page_number"]

        if body_text:
            prev_tail = _emit_text(
                body_text, current_path, pnum, pnum, chunks, prev_tail
            )

        # Recurse into children
        prev_tail = _walk(node["children"], current_path, chunks, prev_tail)

    return prev_tail


def _emit_text(
    text: str,
    section_path: list[str],
    page_start: int,
    page_end: int,
    chunks: list[RawChunk],
    prev_tail: str,
) -> str:
    """Split text into chunks respecting target size, with overlap."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    current_parts: list[str] = []
    current_len = 0

    if prev_tail:
        current_parts.append(prev_tail)
        current_len = len(prev_tail)

    def _flush(parts: list[str]) -> str:
        chunk_text = "\n\n".join(parts).strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "section_path": list(section_path),
                "page_start": page_start,
                "page_end": page_end,
            })
            # return tail for overlap
            return chunk_text[-_OVERLAP:] if len(chunk_text) > _OVERLAP else chunk_text
        return ""

    for para in paragraphs:
        para_len = len(para)

        if current_len + para_len > _TARGET_MAX and current_len >= _TARGET_MIN:
            prev_tail = _flush(current_parts)
            current_parts = [prev_tail, para] if prev_tail else [para]
            current_len = len(prev_tail) + para_len
        else:
            current_parts.append(para)
            current_len += para_len

    if current_parts:
        prev_tail = _flush(current_parts)

    return prev_tail
