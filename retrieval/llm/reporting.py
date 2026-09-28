from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ErrorHook = Callable[..., Awaitable[None]]

_hook: ContextVar[ErrorHook | None] = ContextVar("llm_error_hook", default=None)


def set_error_hook(hook: ErrorHook | None) -> None:
    _hook.set(hook)


async def report(**fields: Any) -> None:
    """Fire the current request's error hook. Never raises."""
    hook = _hook.get()
    if hook is None:
        logger.warning("LLM error (no hook bound): %s", fields)
        return
    try:
        await hook(**fields)
    except Exception:
        logger.exception("LLM error hook failed: %s", fields)
