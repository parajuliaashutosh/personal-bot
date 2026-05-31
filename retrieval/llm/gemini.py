from __future__ import annotations

import asyncio
from typing import AsyncIterator

import google.generativeai as genai

from shared.config.settings import settings

genai.configure(api_key=settings.gemini_api_key)

_chat_model = genai.GenerativeModel(settings.gemini_model)


async def generate(
    prompt: str,
    history: list[dict[str, str]],
) -> AsyncIterator[str]:
    gemini_history = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]}
        for m in history
    ]
    chat = _chat_model.start_chat(history=gemini_history)

    response = await asyncio.to_thread(
        lambda: chat.send_message(prompt, stream=True)
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text


async def embed(texts: list[str]) -> list[list[float]]:
    results: list[list[float]] = []
    for text in texts:
        result = await asyncio.to_thread(
            lambda t=text: genai.embed_content(
                model=f"models/{settings.gemini_embed_model}",
                content=t,
                task_type="retrieval_document",
            )
        )
        results.append(result["embedding"])
    return results
