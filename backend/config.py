from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Work OS Backend"
    app_env: str = Field(default="development", alias="AIWORKOS_ENV")
    app_host: str = Field(default="0.0.0.0", alias="AIWORKOS_HOST")
    app_port: int = Field(default=8000, alias="AIWORKOS_PORT")
    database_url: str = Field(default="sqlite+aiosqlite:///./backend/db/aiworkos.db", alias="AIWORKOS_DATABASE_URL")
    default_model: str = Field(default="gpt-4.1", alias="AIWORKOS_DEFAULT_MODEL")
    research_model: str = Field(default="gpt-4.1-mini", alias="AIWORKOS_RESEARCH_MODEL")
    marketing_model: str = Field(default="gpt-4.1-mini", alias="AIWORKOS_MARKETING_MODEL")
    coding_model: str = Field(default="gpt-4.1", alias="AIWORKOS_CODING_MODEL")
    log_level: str = Field(default="INFO", alias="AIWORKOS_LOG_LEVEL")
    mcp_disable_dns_rebinding_protection: bool = Field(
        default=False,
        alias="AIWORKOS_MCP_DISABLE_DNS_REBINDING_PROTECTION",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
