import re
import unicodedata

_MAX_LENGTH = 1000

_INJECTION_PATTERNS = re.compile(
    r"ignore previous|you are now|forget instructions|new instructions|system:|<\||>",
    re.IGNORECASE,
)


def sanitize_query(query: str) -> tuple[str, str | None]:
    query = unicodedata.normalize("NFKC", query)

    if len(query) > _MAX_LENGTH:
        return "", "query_too_long"

    cleaned = _INJECTION_PATTERNS.sub("", query).strip()

    if not cleaned:
        return "", "query_empty_after_sanitization"

    return cleaned, None
