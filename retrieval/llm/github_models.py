from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from shared.config.settings import settings

_BASE_URL = "https://models.inference.ai.azure.com"


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

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
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
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                chunk = json.loads(data)
                token = (
                    chunk.get("choices", [{}])[0]
                    .get("delta", {})
                    .get("content", "")
                )
                if token:
                    yield token
