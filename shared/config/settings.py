from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str

    # LLM provider
    llm_provider: str = "gemini"  # "gemini" | "ollama"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "text-embedding-004"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # Security
    api_key: str

    # Ingestion limits
    max_file_size_mb: int = 50
    max_pages: int = 500
    pdf_dir: str = "pdfs"
    embed_batch_size: int = 20

    # Retrieval limits
    context_token_limit: int = 3000


settings = Settings()
