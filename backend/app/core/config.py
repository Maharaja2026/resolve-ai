"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ResolveAI"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Supabase (shared project with KnowledgePilot; ResolveAI uses namespaced tables)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""

    # LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    llm_primary_provider: str = "gemini"
    llm_fallback_provider: str = "groq"
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 1

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # Agent limits
    max_agent_steps: int = 10
    max_tool_calls: int = 8
    agent_timeout_seconds: int = 120
    chat_history_window: int = 8

    # Checkpointing
    checkpointer_backend: str = "sqlite"
    checkpoint_database_path: str = ".data/resolveai_checkpoints.sqlite"

    # Business rules
    return_window_days: int = 30
    late_delivery_grace_days: int = 3
    max_simulated_refund_amount: float = 5000.0
    approval_expiry_hours: int = 48

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 15
    rrf_k: int = 60

    cors_origins: str = "http://localhost:3001"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key and self.supabase_anon_key)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
