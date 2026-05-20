# app/llm/gemini.py
import os
from typing import List, Dict, AsyncGenerator
from google import genai
from google.genai import types
from app.llm.base import BaseLLM


class GeminiLLM(BaseLLM):
    def __init__(self, model: str = "gemini-2.5-flash"):
        print(f"Running model: {model} via Google GenAI")
        # Client automatically reads GEMINI_API_KEY from environment variables
        self.client = genai.Client()
        self.model = model

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[types.Content]:
        """Converts OpenAI/Ollama style message format to Gemini's expected types."""
        formatted_contents = []
        for msg in messages:
            role = msg.get("role")
            # Map common 'assistant' role nomenclature to Gemini's expected 'model' role
            if role == "assistant":
                role = "model"

            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get("content", ""))]
                )
            )
        return formatted_contents

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        contents = self._convert_messages(messages)
        # Using the async client (.aio) provided by the new google-genai SDK
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
        )
        return response.text

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        contents = self._convert_messages(messages)
        response_stream = await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,
        )
        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text
