import re
import unicodedata

from shared.errors import AppError, QUERY_TOO_LONG, QUERY_INJECTION

_MAX_LENGTH = 1000

_INJECTION_PATTERNS = re.compile(
    r"ignore previous|you are now|forget instructions|new instructions|system:|<\||\|>",
    re.IGNORECASE,
)


def sanitize_query(query: str) -> tuple[str, AppError | None]:
    query = unicodedata.normalize("NFKC", query)

    if len(query) > _MAX_LENGTH:
        return "", AppError(code=QUERY_TOO_LONG, message="Query exceeds maximum allowed length")

    if _INJECTION_PATTERNS.search(query):
        return "", AppError(code=QUERY_INJECTION, message="Query contains disallowed patterns")

    cleaned = _INJECTION_PATTERNS.sub("", query).strip()

    if not cleaned:
        return "", AppError(code=QUERY_INJECTION, message="Query is empty after sanitization")

    return cleaned, None
