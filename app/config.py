import os
from app.llm.ollama import OllamaLLM

def get_llm():
    return OllamaLLM(os.getenv("OLLAMA_MODEL", "llama3.2"))
