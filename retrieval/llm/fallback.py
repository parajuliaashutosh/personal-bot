from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Callable

from retrieval.llm.errors import ProviderFailure, StreamTruncated
from retrieval.llm.guards import StreamCutShort, StreamStalled
from retrieval.llm.reporting import report
from shared.config.settings import settings
from shared.errors import LLM_PROVIDER_ERROR, STREAM_TRUNCATED

logger = logging.getLogger(__name__)

_RETRYABLE_SUBSTRINGS = (
    "429",
    "quota",
    "exhausted",
    "service unavailable",
    "503",
    "502",
    "504",
    "overloaded",
    "rate limit",
    "too many requests",
    "timeout",
    "timed out",
    "connection reset",
    "connection aborted",
    "server disconnected",
    "incomplete chunked read",
    "peer closed connection",
    "temporarily unavailable",
)

GenerateFn = Callable[..., AsyncIterator[str]]


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, ConnectionError,
                        StreamStalled, StreamCutShort)):
        return True
    msg = str(exc).lower()
    return any(s in msg for s in _RETRYABLE_SUBSTRINGS)


def provider_name(fn: GenerateFn) -> str:
    name = getattr(fn, "_provider_name", None)
    if name:
        return name
    return getattr(fn, "__module__", "unknown").rsplit(".", 1)[-1]


def _tag(fn: GenerateFn, name: str) -> GenerateFn:
    fn._provider_name = name  # type: ignore[attr-defined]
    return fn


def _continuation_prompt(prompt: str, partial: str) -> str:
    """Ask the next provider to finish an answer that was cut off mid-stream."""
    return (
        f"{prompt}\n\n"
        "---\n"
        "You already started answering, and your reply was cut off mid-sentence. "
        "Here is exactly what has already been shown to the user:\n\n"
        f"<<<{partial}>>>\n\n"
        "Continue seamlessly from that exact point and finish the answer. "
        "Do not greet, do not restate, and do not repeat any word already shown — "
        "your output is appended directly to the text above."
    )


def with_retry(
    fn: GenerateFn,
    *,
    attempts: int | None = None,
    base_delay: float | None = None,
) -> GenerateFn:
    """Retry one provider on transient failures.

    Only retries while nothing has been yielded yet — once a token is on the
    wire, restarting would duplicate text, so the failure is raised for
    `with_fallback` (or the route) to handle as a truncation.
    """
    attempts = attempts or settings.llm_retry_attempts
    base_delay = base_delay if base_delay is not None else settings.llm_retry_base_delay
    name = provider_name(fn)

    async def _generate(prompt: str, history: list[dict[str, str]]) -> AsyncIterator[str]:
        failures: list[tuple[int, Exception]] = []

        for attempt in range(attempts):
            yielded = False
            try:
                async for token in fn(prompt, history):
                    yielded = True
                    yield token
            except Exception as exc:
                if yielded:
                    # Tokens already sent — a retry would duplicate them.
                    await report(
                        code=STREAM_TRUNCATED, provider=name, attempt=attempt,
                        recovered=False, exc=exc,
                    )
                    raise
                failures.append((attempt, exc))
                if attempt == attempts - 1 or not _is_retryable(exc):
                    for failed_attempt, failed_exc in failures:
                        await report(
                            code=LLM_PROVIDER_ERROR, provider=name,
                            attempt=failed_attempt, recovered=False, exc=failed_exc,
                        )
                    raise ProviderFailure(name, attempt + 1, exc) from exc

                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "%s attempt %d/%d failed (%s) — retrying in %.1fs",
                    name, attempt + 1, attempts, exc, delay,
                )
                await asyncio.sleep(delay)
                continue

            # Success. Record any attempts we silently recovered from.
            for failed_attempt, failed_exc in failures:
                await report(
                    code=LLM_PROVIDER_ERROR, provider=name,
                    attempt=failed_attempt, recovered=True, exc=failed_exc,
                )
            return

    return _tag(_generate, name)


def with_fallback(primary: GenerateFn, fallback: GenerateFn) -> GenerateFn:
    """Route around a dead provider — including one that dies mid-answer.

    Before the first token: switch to the fallback silently.
    After the first token: ask the fallback to *continue* the partial answer
    (settings.llm_continue_on_truncation). If that also fails, raise
    StreamTruncated carrying the partial so the caller can save it and tell
    the client the reply is incomplete.
    """
    primary_name = provider_name(primary)
    fallback_name = provider_name(fallback)

    async def _generate(prompt: str, history: list[dict[str, str]]) -> AsyncIterator[str]:
        partial: list[str] = []
        primary_exc: Exception | None = None

        try:
            async for token in primary(prompt, history):
                partial.append(token)
                yield token
        except Exception as exc:
            primary_exc = exc

        if primary_exc is None:
            return

        partial_text = "".join(partial)

        # Nothing streamed yet — a clean switch, the client never notices.
        if not partial_text:
            logger.warning(
                "%s unavailable (%s) — falling back to %s",
                primary_name, primary_exc, fallback_name,
            )
            async for token in fallback(prompt, history):
                yield token
            await report(
                code=LLM_PROVIDER_ERROR, provider=primary_name, attempt=0,
                recovered=True, exc=primary_exc,
                context={"fell_back_to": fallback_name},
            )
            return

        # Mid-answer break — try to have the fallback finish the sentence.
        if settings.llm_continue_on_truncation:
            logger.warning(
                "%s broke after %d chars (%s) — continuing with %s",
                primary_name, len(partial_text), primary_exc, fallback_name,
            )
            try:
                async for token in fallback(
                    _continuation_prompt(prompt, partial_text), history
                ):
                    partial.append(token)
                    yield token
            except Exception as exc:
                raise StreamTruncated(
                    "".join(partial), primary_name, primary_exc
                ) from exc
            await report(
                code=STREAM_TRUNCATED, provider=primary_name, attempt=0,
                recovered=True, exc=primary_exc,
                partial_len=len(partial_text),
                context={"continued_by": fallback_name},
            )
            return

        raise StreamTruncated(partial_text, primary_name, primary_exc)

    return _tag(_generate, f"{primary_name}->{fallback_name}")
