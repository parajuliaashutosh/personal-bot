from __future__ import annotations

from pathlib import Path

import fitz  # pymupdf

from shared.config.settings import settings


def validate_pdf(file_path: str) -> tuple[bool, str | None]:
    path = Path(file_path)

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        return False, f"file_too_large:{size_mb:.1f}mb"

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return False, f"cannot_open:{e}"

    if doc.is_encrypted:
        doc.close()
        return False, "encrypted"

    page_count = doc.page_count
    if page_count < 1:
        doc.close()
        return False, "no_pages"

    if page_count > settings.max_pages:
        doc.close()
        return False, f"too_many_pages:{page_count}"

    has_text = any(doc[i].get_text().strip() for i in range(min(page_count, 5)))
    doc.close()

    if not has_text:
        return False, "no_extractable_text"

    return True, None
