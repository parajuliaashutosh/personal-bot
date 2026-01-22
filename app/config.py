import os

from dotenv import load_dotenv
from app.llm.ollama import OllamaLLM


def get_llm():
    load_dotenv()
    return OllamaLLM(os.getenv("OLLAMA_MODEL", "llama3.2"))
