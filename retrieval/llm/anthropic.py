from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from retrieval.llm.guards import INCOMPLETE_STOP_REASONS, StreamCutShort
from shared.config.settings import settings

_client = httpx.AsyncClient(timeout=120.0)


async def generate(
    prompt: str,
    history: list[dict[str, str]],
) -> AsyncIterator[str]:
    """Stream from any Anthropic Messages-compatible endpoint.

    Defaults to DeepSeek's Anthropic-compatible API (ANTHROPIC_BASE_URL), so a
    DeepSeek key works here; point it at https://api.anthropic.com for Claude.
    """
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history if m["role"] in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": prompt})

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with _client.stream(
        "POST",
        f"{settings.anthropic_base_url.rstrip('/')}/v1/messages",
        headers=headers,
        json={
            "model": settings.anthropic_model,
            "max_tokens": settings.anthropic_max_tokens,
            "messages": messages,
            "stream": True,
        },
    ) as resp:
        resp.raise_for_status()
        stop_reason: str | None = None
        saw_stop = False

        async for line in resp.aiter_lines():
            # Skip "event:" lines and keep-alives; every payload is on a "data:" line.
            if not line or not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue

            etype = event.get("type")
            if etype == "error":
                err = event.get("error") or {}
                raise RuntimeError(
                    f"anthropic stream error: {err.get('message', err)}"
                    f" (type={err.get('type')})"
                )
            if etype == "content_block_delta":
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta" and (token := delta.get("text")):
                    yield token
            elif etype == "message_delta":
                stop_reason = (event.get("delta") or {}).get("stop_reason") or stop_reason
            elif etype == "message_stop":
                saw_stop = True
                break

        if stop_reason and stop_reason in INCOMPLETE_STOP_REASONS:
            raise StreamCutShort("anthropic", stop_reason)
        if not saw_stop and not stop_reason:
            raise StreamCutShort("anthropic", "connection_closed")
