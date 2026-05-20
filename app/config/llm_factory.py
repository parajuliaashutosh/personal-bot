from app.config import settings
from app.llm.base import BaseLLM
from app.llm.ollama import OllamaLLM
from app.llm.gemini import GeminiLLM


def get_llm() -> BaseLLM:
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM(model=settings.GEMINI_MODEL)
    elif settings.LLM_PROVIDER == "ollama":
        return OllamaLLM(model=settings.OLLAMA_MODEL, host=settings.OLLAMA_HOST)
    else:
        raise ValueError(f"Unknown provider: {settings.LLM_PROVIDER}")
