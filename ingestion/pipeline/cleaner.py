from __future__ import annotations

import re
from collections import Counter

from ingestion.pipeline.extractor import Block, PageData

_MIN_CHARS = 10
_MAX_NON_ALNUM_RATIO = 0.30
_BOILERPLATE_THRESHOLD = 3  # same text on N+ pages → boilerplate


def _non_alnum_ratio(text: str) -> float:
    if not text:
        return 1.0
    non_alnum = sum(1 for c in text if not c.isalnum() and not c.isspace())
    return non_alnum / len(text)


def _is_page_number(text: str, bbox: tuple, page_height: float) -> bool:
    """Pure digit block near top or bottom 10% of page."""
    if not re.fullmatch(r"\d+", text.strip()):
        return False
    _, y0, _, y1 = bbox
    return y0 < page_height * 0.10 or y1 > page_height * 0.90


def clean_pages(pages: list[PageData]) -> list[PageData]:
    # Count how many pages each block text appears on
    text_page_count: Counter[str] = Counter()
    for page in pages:
        seen_on_page = {b["text"].strip() for b in page["blocks"] if b["text"].strip()}
        text_page_count.update(seen_on_page)

    boilerplate = {t for t, c in text_page_count.items() if c >= _BOILERPLATE_THRESHOLD}

    # Estimate page height from bbox of all blocks (fallback 842 = A4)
    def _page_height(page: PageData) -> float:
        bboxes = [b["bbox"] for b in page["blocks"] if b["bbox"]]
        return max((b[3] for b in bboxes), default=842.0)

    cleaned: list[PageData] = []
    for page in pages:
        ph = _page_height(page)
        kept: list[Block] = []
        for block in page["blocks"]:
            text = block["text"].strip()
            if not text:
                continue
            if len(text) < _MIN_CHARS:
                continue
            if _non_alnum_ratio(text) > _MAX_NON_ALNUM_RATIO:
                continue
            if text in boilerplate:
                continue
            if block["block_type"] == "text" and _is_page_number(text, block["bbox"], ph):
                continue
            kept.append(block)
        cleaned.append({"page_number": page["page_number"], "blocks": kept})

    return cleaned
