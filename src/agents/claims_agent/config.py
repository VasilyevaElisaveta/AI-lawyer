from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── GigaChat ──────────────────────────────────────────────
    gigachat_credentials: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"
    gigachat_verify_ssl: bool = False
    gigachat_temperature: float = 0.1
    gigachat_max_tokens: int = 8192
    gigachat_timeout: int = 180

    # ── Пути ──────────────────────────────────────────────────
    vector_db_path: str = "data/vector_store"
    knowledge_base_path: str = "data/knowledge_base"
    templates_path: str = "data/templates"

    # ── Ограничения графа ─────────────────────────────────────
    max_validation_retries: int = 2
    max_qa_retries: int = 2

    # ── Логирование ───────────────────────────────────────────
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
