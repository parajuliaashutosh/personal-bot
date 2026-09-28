from __future__ import annotations

from typing import AsyncIterator

from google import genai
from google.genai import types

from retrieval.llm.guards import INCOMPLETE_GEMINI_REASONS, StreamCutShort
from shared.config.settings import settings

_client = genai.Client(api_key=settings.gemini_api_key)


async def generate(
    prompt: str,
    history: list[dict[str, str]],
) -> AsyncIterator[str]:
    contents: list[dict] = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in history
    ]
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    stream = await _client.aio.models.generate_content_stream(
        model=settings.gemini_model,
        contents=contents,
    )

    finish_reason: str | None = None

    async for chunk in stream:
        # Gemini reports RECITATION / SAFETY / MAX_TOKENS by ending the stream
        # without raising — the client just sees a sentence stop mid-word.
        for candidate in (chunk.candidates or []):
            if candidate.finish_reason is not None:
                finish_reason = getattr(
                    candidate.finish_reason, "name", str(candidate.finish_reason)
                )
        if chunk.text:
            yield chunk.text

    if finish_reason and finish_reason in INCOMPLETE_GEMINI_REASONS:
        raise StreamCutShort("gemini", finish_reason)


async def embed(texts: list[str]) -> list[list[float]]:
    results: list[list[float]] = []
    for text in texts:
        response = await _client.aio.models.embed_content(
            model=settings.gemini_embed_model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=settings.embed_dimensions,
            ),
        )
        results.append(list(response.embeddings[0].values))
    return results
