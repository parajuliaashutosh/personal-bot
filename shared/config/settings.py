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
    max_query_vectors: int = 2       # query + variations embedded per chat
    llm_query_expansion: bool = False  # true = +1 generate call per chat
    llm_rerank: bool = False           # true = +1 generate call per chat
    rerank_relevance_weight: float = 0.5  # lower = more diverse passages

    # Generation resilience
    llm_retry_attempts: int = 3          # per provider, only before the first token
    llm_retry_base_delay: float = 0.5    # seconds; doubles each attempt
    llm_stream_idle_timeout: float = 45.0  # seconds without a token = dead stream
    llm_continue_on_truncation: bool = True  # let the fallback finish a cut-off answer

    chat_rate_limit: str = "2/minute"   # new questions; a retry is free here
    chat_burst_limit: str = "8/minute"  # hard ceiling, charged on every request
    client_max_retries: int = 2          # advertised to the frontend in error events
    client_retry_after_ms: int = 1200    # base backoff advertised to the frontend

    prompts_dir: str = "prompts"


settings = Settings()
