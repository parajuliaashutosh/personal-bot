from __future__ import annotations

import logging
from typing import AsyncIterator, Callable

logger = logging.getLogger(__name__)

_RETRYABLE_SUBSTRINGS = (
    "429",
    "quota",
    "exhausted",
    "service unavailable",
    "503",
    "overloaded",
    "rate limit",
    "too many requests",
)

GenerateFn = Callable[..., AsyncIterator[str]]


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in _RETRYABLE_SUBSTRINGS)


def with_fallback(primary: GenerateFn, fallback: GenerateFn) -> GenerateFn:
    async def _generate(
        prompt: str,
        history: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        tokens_seen: list[str] = []
        failed = False

        try:
            async for token in primary(prompt, history):
                tokens_seen.append(token)
                yield token
        except Exception as exc:
            if tokens_seen or not _is_retryable(exc):
                raise
            failed = True
            logger.warning("Primary LLM unavailable (%s), switching to fallback", exc)

        if failed:
            async for token in fallback(prompt, history):
                yield token

    return _generate
