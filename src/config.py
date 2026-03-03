import logging
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"  # development | staging | production

    database_url: str = "sqlite+aiosqlite:///./mcdr_mock/mcdr_cx.db"
    customer_db_url: str = "sqlite+aiosqlite:///./mcdr_mock/mcdr_cx.db"

    secret_key: str = "poc-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_ssl: str = ""  # "" (off), "require", or "verify-full"

    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    mcdr_core_db_path: str = "mcdr_mock/mcdr_core.db"
    mcdr_mobile_db_path: str = "mcdr_mock/mcdr_mobile.db"
    mcdr_cx_db_path: str = "mcdr_mock/mcdr_cx.db"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_production(self) -> None:
        if self.environment == "production":
            if "poc-secret" in self.secret_key or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not the default POC key"
                )
            if "localhost" in self.cors_origins:
                logging.getLogger("mcdr").warning(
                    "CORS_ORIGINS contains localhost — verify this is intentional for production"
                )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_for_production()
    return s
