from __future__ import annotations

import re
import statistics
from typing import TypedDict

from ingestion.pipeline.extractor import Block, PageData


class SectionNode(TypedDict):
    level: int
    title: str
    page_number: int
    children: list["SectionNode"]
    blocks: list[Block]


def detect_structure(pages: list[PageData]) -> list[SectionNode]:
    all_blocks: list[tuple[Block, int]] = [
        (b, p["page_number"])
        for p in pages
        for b in p["blocks"]
        if b["block_type"] == "text" and b["text"].strip()
    ]

    if not all_blocks:
        return []

    font_sizes = [b["font_size"] for b, _ in all_blocks if b["font_size"] > 0]
    median_size = statistics.median(font_sizes) if font_sizes else 0.0

    # Try font-size based heading detection
    heading_sizes = sorted(
        {s for s in font_sizes if s > median_size + 2},
        reverse=True,
    )

    def _font_level(size: float) -> int | None:
        for i, hs in enumerate(heading_sizes[:3], start=1):
            if abs(size - hs) < 0.5:
                return i
        return None

    # Fallback regex patterns
    _H1_RE = re.compile(r"^[A-Z][A-Z\s]{4,}$")
    _NUM_RE = re.compile(r"^(\d+)\.(\d+)?\.?(\d+)?\.?\s+\S")

    def _regex_level(text: str) -> int | None:
        t = text.strip()
        if _H1_RE.match(t):
            return 1
        m = _NUM_RE.match(t)
        if m:
            parts = [g for g in m.groups() if g is not None]
            return min(len(parts), 3)
        return None

    use_font = len(heading_sizes) > 0

    def _level(block: Block) -> int | None:
        if use_font:
            return _font_level(block["font_size"])
        return _regex_level(block["text"])

    # Build flat list of (level, block, page_number)
    items: list[tuple[int, Block, int]] = []
    for block, pnum in all_blocks:
        lvl = _level(block)
        items.append((lvl or 0, block, pnum))

    # Build section tree
    roots: list[SectionNode] = []
    stack: list[SectionNode] = []  # stack of open sections by level

    def _current_body_target() -> SectionNode | None:
        return stack[-1] if stack else None

    for lvl, block, pnum in items:
        if lvl == 0:
            # body block — attach to current section
            target = _current_body_target()
            if target is not None:
                target["blocks"].append(block)
            else:
                # no section yet — create implicit root
                node: SectionNode = {
                    "level": 0,
                    "title": "",
                    "page_number": pnum,
                    "children": [],
                    "blocks": [block],
                }
                roots.append(node)
                stack = [node]
        else:
            node = {
                "level": lvl,
                "title": block["text"].strip(),
                "page_number": pnum,
                "children": [],
                "blocks": [],
            }
            # pop stack until we find a parent of lower level
            while stack and stack[-1]["level"] >= lvl:
                stack.pop()

            if stack:
                stack[-1]["children"].append(node)
            else:
                roots.append(node)

            stack.append(node)

    return roots
