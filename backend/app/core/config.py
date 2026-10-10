from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    web_origin: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://lenny:lenny@localhost:5432/lenny"

    llm_provider: Literal["ollama", "anthropic", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "embeddinggemma"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    agent_url: str = "http://localhost:3001"

    top_k: int = Field(default=10, ge=1, le=20)
    min_retrieval_score: float = Field(default=0.18, ge=0, le=1)
    max_history_messages: int = Field(default=8, ge=2, le=20)
    corpus_git_sha: str = "uninitialized"
    demo_mode: bool = True

    @property
    def active_model(self) -> str:
        return {
            "ollama": self.ollama_model,
            "anthropic": self.anthropic_model,
            "openai": self.openai_model,
        }[self.llm_provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()

