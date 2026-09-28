from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from retrieval.llm.guards import INCOMPLETE_FINISH_REASONS, StreamCutShort
from shared.config.settings import settings

_BASE_URL = "https://models.inference.ai.azure.com"
_client = httpx.AsyncClient(timeout=120.0)


async def generate(
    prompt: str,
    history: list[dict[str, str]],
) -> AsyncIterator[str]:
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {settings.github_models_token}",
        "Content-Type": "application/json",
    }

    async with _client.stream(
        "POST",
        f"{_BASE_URL}/chat/completions",
        headers=headers,
        json={
            "model": settings.github_models_model,
            "messages": messages,
            "stream": True,
        },
    ) as resp:
        resp.raise_for_status()
        finish_reason: str | None = None
        saw_done = False

        async for line in resp.aiter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                saw_done = True
                break

            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            # Mid-stream error payloads arrive with a 200 status. Without this
            # check the stream just stops and the user sees half an answer.
            if err := chunk.get("error"):
                raise RuntimeError(
                    f"github_models stream error: {err.get('message', err)}"
                    f" (code={err.get('code')})"
                )

            choice = (chunk.get("choices") or [{}])[0]
            finish_reason = choice.get("finish_reason") or finish_reason
            if token := (choice.get("delta") or {}).get("content"):
                yield token

        if finish_reason and finish_reason in INCOMPLETE_FINISH_REASONS:
            raise StreamCutShort("github_models", finish_reason)
        if not saw_done and not finish_reason:
            raise StreamCutShort("github_models", "connection_closed")
