from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class LLMFn(Protocol):
    async def __call__(
        self,
        prompt: str,
        history: list[dict[str, str]],
    ) -> AsyncIterator[str]: ...


@runtime_checkable
class EmbedFn(Protocol):
    async def __call__(self, texts: list[str]) -> list[list[float]]: ...
