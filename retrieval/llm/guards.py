from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Callable

from shared.config.settings import settings

logger = logging.getLogger(__name__)

GenerateFn = Callable[..., AsyncIterator[str]]


class StreamStalled(TimeoutError):
    """No token arrived within the idle window — the upstream stream is dead."""


class StreamCutShort(Exception):
    """The provider closed the stream cleanly but before the answer finished.

    This is the silent version of the bug: no exception, no error payload, the
    connection just ends mid-sentence. Providers raise it explicitly so the
    retry/fallback layer can treat it like any other failure.
    """

    def __init__(self, provider: str, reason: str):
        super().__init__(f"{provider} ended the stream early (finish_reason={reason})")
        self.provider = provider
        self.reason = reason


# OpenAI-style finish reasons that mean "this answer is not complete".
INCOMPLETE_FINISH_REASONS = {"length", "content_filter", "error"}
# Gemini finish reasons that mean the same thing.
INCOMPLETE_GEMINI_REASONS = {"MAX_TOKENS", "SAFETY", "RECITATION", "BLOCKLIST",
                             "PROHIBITED_CONTENT", "SPII", "MALFORMED_FUNCTION_CALL", "OTHER"}


def with_idle_timeout(fn: GenerateFn, timeout: float | None = None) -> GenerateFn:
    """Fail fast when a provider stops sending tokens but never closes the connection.

    Without this a hung upstream just holds the SSE connection open until the
    browser or proxy gives up, which the user sees as a half-finished answer.
    """
    limit = timeout if timeout is not None else settings.llm_stream_idle_timeout
    name = getattr(fn, "_provider_name", getattr(fn, "__module__", "llm").rsplit(".", 1)[-1])

    async def _generate(prompt: str, history: list[dict[str, str]]) -> AsyncIterator[str]:
        agen = fn(prompt, history).__aiter__()
        try:
            while True:
                try:
                    token = await asyncio.wait_for(agen.__anext__(), limit)
                except StopAsyncIteration:
                    return
                except asyncio.TimeoutError as exc:
                    raise StreamStalled(
                        f"{name} sent no token for {limit:.0f}s"
                    ) from exc
                yield token
        finally:
            aclose = getattr(agen, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()
                except Exception:  # noqa: BLE001
                    logger.debug("aclose on %s stream failed", name, exc_info=True)

    _generate._provider_name = name  # type: ignore[attr-defined]
    return _generate
