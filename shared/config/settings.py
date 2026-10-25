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

    # LLM providers — chain: primary → the other one (each skipped if key absent)
    llm_provider: str = "openrouter"  # primary: "openrouter" | "anthropic"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"

    # Anthropic Messages API format. Defaults to DeepSeek's Anthropic-compatible
    # endpoint, so a DeepSeek key goes in ANTHROPIC_API_KEY; set the base URL to
    # https://api.anthropic.com (and a Claude model) to use Anthropic itself.
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.deepseek.com/anthropic"
    anthropic_model: str = "deepseek-chat"
    anthropic_max_tokens: int = 4096

    # Embeddings — the chat providers may lack an embeddings endpoint, so this is any
    # OpenAI-compatible /embeddings service; defaults to OpenRouter.
    embed_base_url: str = "https://openrouter.ai/api/v1"
    embed_api_key: str = ""  # falls back to OPENROUTER_API_KEY
    embed_model: str = "openai/text-embedding-3-small"
    embed_dimensions: int = 768  # must match vector(N) in DB schema

    # Security — two route-scoped keys
    api_key: str       # valid on /chat/* only

    # Admin login — short-lived JWT access token plus a rotating refresh token
    jwt_secret: str = ""           # required, >= 32 chars (e.g. `openssl rand -hex 32`)
    jwt_expire_minutes: int = 15
    refresh_expire_days: int = 7
    admin_email: str = ""          # seeded on startup if no such user exists
    admin_password: str = ""
    cookie_name: str = "admin_token"
    refresh_cookie_name: str = "admin_refresh"
    cookie_secure: bool = False    # false for local http dev; set true behind https
    cookie_samesite: str = "lax"   # "lax" | "strict" | "none" (none requires secure)
    cookie_domain: str = ""        # empty = host-only cookie

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
