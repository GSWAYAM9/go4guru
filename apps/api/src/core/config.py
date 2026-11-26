"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime configuration backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core runtime
    app_name: str = Field(default="go4guru-api")
    app_env: Literal["development", "test", "staging", "production"] = Field(default="development")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")

    # Network & CORS
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])

    # Database (PostgreSQL 18 + asyncpg)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/go4guru"
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_echo: bool = Field(default=False)
    database_connect_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)

    # Cache, Queue & PubSub (Redis)
    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)

    # Object Storage (S3-compatible / MinIO / Local Private Archive)
    s3_endpoint_url: str | None = Field(default="http://127.0.0.1:9000")
    s3_region: str = Field(default="ap-south-1")
    s3_access_key_id: str = Field(default="")
    s3_secret_access_key: SecretStr = Field(default=SecretStr(""))
    s3_private_bucket: str = Field(default="go4guru-private")
    storage_local_dir: str = Field(default="./.local/storage")
    max_import_file_bytes: int = Field(default=15 * 1024 * 1024, ge=1024)

    # Security & Auth Baseline
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-only-change-before-deploy-minimum-32-chars")
    )
    jwt_algorithm: Literal["HS256", "RS256"] = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=15, ge=5, le=120)
    jwt_refresh_token_expire_days: int = Field(default=14, ge=1, le=90)
    refresh_cookie_name: str = Field(default="go4guru_refresh_token")
    cookie_secure: bool = Field(default=False)
    password_argon2_time_cost: int = Field(default=3, ge=2, le=10)
    password_argon2_memory_cost: int = Field(default=65536, ge=16384)
    password_argon2_parallelism: int = Field(default=2, ge=1, le=8)

    # Phase 3 AI Providers, Routing, Quotas & Circuit Breaker (Backend Secrets Only)
    gemini_api_key: SecretStr = Field(default=SecretStr(""))
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    ai_primary_provider: Literal["gemini", "openai", "anthropic", "auto"] = Field(default="auto")
    ai_gemini_fast_model: str = Field(default="gemini-2.5-flash")
    ai_gemini_reasoning_model: str = Field(default="gemini-2.5-pro")
    ai_openai_fast_model: str = Field(default="gpt-4o-mini")
    ai_openai_reasoning_model: str = Field(default="gpt-4o")
    ai_anthropic_fast_model: str = Field(default="claude-3-5-haiku-latest")
    ai_anthropic_reasoning_model: str = Field(default="claude-3-7-sonnet-latest")
    ai_request_timeout_seconds: float = Field(default=25.0, ge=2.0, le=120.0)
    ai_daily_turn_limit: int = Field(default=60, ge=1, le=5000)
    ai_rpm_limit: int = Field(default=15, ge=1, le=600)
    ai_max_verifier_retries: int = Field(default=2, ge=0, le=3)

    # Phase 4 Voice Provider (ElevenLabs)
    elevenlabs_api_key: SecretStr = Field(default=SecretStr(""))
    elevenlabs_default_voice_id: str = Field(default="EXAVITQu4vr4xnSDxMaL")
    elevenlabs_model_id: str = Field(default="eleven_multilingual_v2")
    voice_request_timeout_seconds: float = Field(default=20.0, ge=2.0, le=60.0)

    @field_validator("cors_allowed_origins")
    @classmethod
    def reject_wildcard_cors_with_credentials(cls, origins: list[str]) -> list[str]:
        """Disallow wildcard '*' origins because authenticated cookies require explicit origins."""
        if "*" in origins:
            raise ValueError("Wildcard '*' is forbidden in cors_allowed_origins.")
        return origins

    @model_validator(mode="after")
    def validate_non_dev_security_invariants(self) -> Settings:
        """Fail fast if staging/production environments boot with insecure defaults."""
        secret = self.jwt_secret_key.get_secret_value()
        if len(secret) < 32:
            raise ValueError("jwt_secret_key must be at least 32 characters.")
        if self.app_env in {"staging", "production"}:
            if secret.startswith("dev-only") or "CHANGE_ME" in secret:
                raise ValueError(
                    "Staging/production requires an explicit non-default JWT_SECRET_KEY."
                )
            if self.debug:
                raise ValueError("DEBUG=true is forbidden in staging and production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached runtime settings instance."""
    return Settings()
