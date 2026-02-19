from ollama import AsyncClient
from app.llm.base import BaseLLM


class OllamaLLM(BaseLLM):
    def __init__(self, model="llama3.2", host="http://localhost:11434"):
        print(f"Running model: {model} on host: {host}")
        self.client = AsyncClient(host=host)
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
            content = part["message"]["content"]
            if content:
                yield content
