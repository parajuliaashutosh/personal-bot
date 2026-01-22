from ollama import AsyncClient
from app.llm.base import BaseLLM


class OllamaLLM(BaseLLM):
    def __init__(self, model="llama3.2"):
        print("Running model:", model)
        self.client = AsyncClient()
        self.model = model

    async def chat(self, messages):
        res = await self.client.chat(model=self.model, messages=messages)
        return res["message"]["content"]

    async def stream(self, messages):
        stream_response = await self.client.chat(
            model=self.model,
            messages=messages,
            stream=True
        )

        async for part in stream_response:
            yield part["message"]["content"]
