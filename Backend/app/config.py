"""
Application settings loaded from environment variables / .env file.

All runtime configuration lives here so the rest of the app can depend on a
single, typed `Settings` object instead of reading os.environ ad-hoc.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Secrets ---
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude.")
    openai_api_key: str = Field(
        ...,
        description=(
            "OpenAI API key. Required because OpenAIEmbeddings is used to embed "
            "incoming questions before searching ChromaDB."
        ),
    )

    # --- Vector store (must mirror Pipeline/ingest.py) ---
    chroma_dir: str = Field(
        default="../Pipeline/chroma_db",
        description="Path to the persisted Chroma directory created by ingest.py.",
    )
    chroma_mode: str = Field(
    default="embedded",
    description="ChromaDB mode: 'embedded' for local file, 'http' for remote server.",
    )
    chroma_host: str = Field(
        default="localhost",
        description="ChromaDB server host. Only used when chroma_mode=http.",
    )
    chroma_port: int = Field(
        default=8000,
        description="ChromaDB server port. Only used when chroma_mode=http.",
    )

    collection_name: str = Field(
        default="vaughn_personal_docs",
        description="Chroma collection name; must match ingest.py.",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model; must match ingest.py.",
    )

    # --- LLM ---
    claude_model: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model id used for chat completions.",
    )
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    # --- Retrieval ---
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of chunks to retrieve from Chroma per query.",
    )
    min_similarity_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Optional relevance-score floor in [0,1]. Chunks scoring below this "
            "are dropped before being sent to the LLM. Set to e.g. 0.65 to "
            "filter weak matches; leave unset (None) to keep all top_k results."
        ),
    )
    enable_query_expansion: bool = Field(
        default=True,
        description="If true, expand queries with synonym lists before retrieval.",
    )

    # --- BM25 + LLM rerank (Karpathy-style hybrid retrieval) ---
    enable_bm25: bool = Field(
        default=False,
        description=(
            "Default behavior for /api/chat when no use_bm25 query param is "
            "given. false = vector-only (current behavior), true = BM25 first "
            "stage + Claude rerank."
        ),
    )
    bm25_candidates: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of candidates returned by the BM25 first stage.",
    )
    rerank_top_k: int = Field(
        default=8,
        ge=1,
        le=30,
        description="Number of chunks kept after LLM rerank (final context size).",
    )
    rerank_model: str | None = Field(
        default=None,
        description=(
            "Optional Anthropic model id for the rerank call. Defaults to "
            "claude_model. Set to a cheaper/faster model if latency matters."
        ),
    )

    # --- HTTP ---
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Notifications (Telegram) ---
    telegram_bot_token: str | None = Field(
        default=None,
        description="Telegram bot token from @BotFather. Leave unset to disable.",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description="Telegram chat id to receive notifications (from @userinfobot).",
    )
    enable_telegram_notifications: bool = Field(
        default=True,
        description=(
            "Master switch. Even when true, notifications no-op silently if "
            "telegram_bot_token or telegram_chat_id is missing."
        ),
    )
    visit_throttle_seconds: int = Field(
        default=3600,
        ge=0,
        le=86400,
        description=(
            "Per-IP+path throttle for /api/visit notifications, in seconds. "
            "Set to 0 to disable throttling (every refresh pings)."
        ),
    )

    # --- Analytics / visitor storage ---
    sqlite_path: str = Field(
        default="data/visitors.db",
        description="Path to the SQLite database used for visitor and intake storage.",
    )
    admin_key: str = Field(
        default="",
        description="Secret key required to access /api/admin/visitors. Set via ADMIN_KEY env var.",
    )

    # --- Airflow (for triggering DAG 2 after answer submission) ---
    airflow_url: str = Field(
        default="",
        description="Astro Cloud deployment base URL for triggering rag_commit DAG.",
    )
    airflow_username: str = Field(
        default="",
        description="Airflow REST API username.",
    )
    airflow_password: str = Field(
        default="",
        description="Airflow REST API password or token.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
