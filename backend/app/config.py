"""Application configuration."""
from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "Enterprise Management"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/enterprise_mgmt"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/enterprise_mgmt"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    JWT_REFRESH_SECRET_KEY: str = "change-this-to-another-secure-random-secret-key"

    # Password policy (R7)
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_MAX_AGE_DAYS: int = 90
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # TOTP MFA (R7)
    TOTP_ISSUER: str = "Enterprise Management"
    TOTP_ENABLED: bool = False

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # RLS (E5)

    # OpenTelemetry (R2)
    OTEL_EXPORTER_ENDPOINT: str = ""

    # Redis Queue (R3: split from cache Redis)
    REDIS_QUEUE_URL: str = "redis://localhost:6380/0"

    ENABLE_RLS: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
