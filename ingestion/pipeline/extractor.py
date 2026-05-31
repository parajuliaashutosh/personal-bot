from __future__ import annotations

from typing import TypedDict

import fitz  # pymupdf


class Block(TypedDict):
    text: str
    font_size: float
    bbox: tuple[float, float, float, float]
    block_type: str  # "text" | "image" | "table"


class PageData(TypedDict):
    page_number: int
    blocks: list[Block]


def extract_pages(file_path: str) -> list[PageData]:
    doc = fitz.open(file_path)
    pages: list[PageData] = []

    for page in doc:
        blocks: list[Block] = []
        raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for b in raw.get("blocks", []):
            btype = b.get("type", 0)

            if btype == 1:  # image block
                blocks.append({
                    "text": "",
                    "font_size": 0.0,
                    "bbox": tuple(b["bbox"]),
                    "block_type": "image",
                })
                continue

            # text block
            lines_text: list[str] = []
            font_sizes: list[float] = []

            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    t = span.get("text", "")
                    if t:
                        lines_text.append(t)
                        font_sizes.append(span.get("size", 0.0))

            text = "".join(lines_text).strip()
            if not text:
                continue

            avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else 0.0
            blocks.append({
                "text": text,
                "font_size": round(avg_font, 2),
                "bbox": tuple(b["bbox"]),
                "block_type": "text",
            })

        pages.append({"page_number": page.number + 1, "blocks": blocks})

    doc.close()
    return pages
