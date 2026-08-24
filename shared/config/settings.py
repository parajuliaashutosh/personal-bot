from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database — accepts either DATABASE_URL or individual parts
    database_url: str = ""
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "personal_chatbot"

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self

    # LLM provider — chain: primary → github_models → gemini (each skipped if key absent)
    llm_provider: str = "openrouter"  # "openrouter" | "gemini" | "ollama"

    # Gemini (embed always uses this when key present; fallback for generate)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "text-embedding-004"
    embed_dimensions: int = 768  # must match vector(N) in DB schema

    # OpenRouter (primary generate)
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"

    # GitHub Models (secondary generate fallback)
    github_models_token: str = ""
    github_models_model: str = "Meta-Llama-3.1-8B-Instruct"

    # Ollama (local fallback for both embed and generate)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # Security — two route-scoped keys
    api_key: str       # valid on /chat/* only
    admin_key: str     # valid on /ingest/* and /admin/* only

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000", "http://localhost:3001"]

    # Geo enrichment (optional)
    ipinfo_api_key: str = ""

    # Ingestion limits
    max_file_size_mb: int = 50
    max_pages: int = 500
    data_dir: str = "data"
    embed_batch_size: int = 20

    # Retrieval limits
    context_token_limit: int = 3000

    # System prompts — markdown files loaded at startup (missing file = fatal)
    prompts_dir: str = "prompts"


settings = Settings()
