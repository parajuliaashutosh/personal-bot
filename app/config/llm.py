import os

from dotenv import load_dotenv
from app.llm.ollama import OllamaLLM


def get_llm():
    load_dotenv()
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    return OllamaLLM(model=ollama_model, host=ollama_host)
