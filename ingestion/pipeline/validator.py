from __future__ import annotations

from pathlib import Path

import fitz  # pymupdf

from shared.config.settings import settings
from shared.errors import (
    AppError,
    PDF_ENCRYPTED,
    PDF_NO_TEXT,
    PDF_PAGE_COUNT,
    PDF_TOO_LARGE,
    PDF_UNREADABLE,
)


async def validate_pdf(file_path: str) -> tuple[bool, AppError | None]:
    path = Path(file_path)

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        return False, AppError(
            code=PDF_TOO_LARGE,
            message=f"PDF exceeds {settings.max_file_size_mb} MB limit ({size_mb:.1f} MB)",
        )

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        return False, AppError(code=PDF_UNREADABLE, message=f"PDF cannot be opened: {exc}")

    if doc.is_encrypted:
        doc.close()
        return False, AppError(code=PDF_ENCRYPTED, message="PDF is password protected")

    page_count = doc.page_count
    if not (1 <= page_count <= settings.max_pages):
        doc.close()
        return False, AppError(
            code=PDF_PAGE_COUNT,
            message=f"PDF has {page_count} pages (allowed: 1–{settings.max_pages})",
        )

    has_text = any(doc[i].get_text().strip() for i in range(min(page_count, 5)))
    doc.close()

    if not has_text:
        return False, AppError(code=PDF_NO_TEXT, message="PDF has no extractable text")

    return True, None
