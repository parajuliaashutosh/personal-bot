from __future__ import annotations


class ProviderFailure(Exception):
    """A single provider gave up after exhausting its retries."""

    def __init__(self, provider: str, attempts: int, cause: BaseException):
        super().__init__(f"{provider} failed after {attempts} attempt(s): {cause}")
        self.provider = provider
        self.attempts = attempts
        self.cause = cause


class StreamTruncated(Exception):
    """The stream broke *after* tokens reached the client, and could not be continued.

    Carries the partial answer so the caller can persist it and tell the client
    exactly how much it already has.
    """

    def __init__(self, partial: str, provider: str, cause: BaseException | None = None):
        super().__init__(f"stream from {provider} truncated after {len(partial)} chars: {cause}")
        self.partial = partial
        self.provider = provider
        self.cause = cause
