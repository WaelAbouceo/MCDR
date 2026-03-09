import logging
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


_POC_SECRET = "poc-secret-key-change-in-production"


class Settings(BaseSettings):
    environment: str = "development"  # development | staging | production

    database_url: str = "mysql+aiomysql://mcdr:mcdr_pass@localhost:3306/mcdr_cx"
    customer_db_url: str = "mysql+aiomysql://mcdr:mcdr_pass@localhost:3306/mcdr_customer"

    secret_key: str = _POC_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_ssl: str = ""  # "" (off), "require", or "verify-full"

    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    # AI: enabled by default; set OPENAI_API_KEY to activate semantic search, categorization, etc.
    openai_api_key: str = ""
    ai_enabled: bool = True

    mcdr_core_db_url: str = "mysql+pymysql://mcdr:mcdr_pass@localhost:3306/mcdr_core"
    mcdr_mobile_db_url: str = "mysql+pymysql://mcdr:mcdr_pass@localhost:3306/mcdr_mobile"
    mcdr_cx_db_url: str = "mysql+pymysql://mcdr:mcdr_pass@localhost:3306/mcdr_cx"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def _parse_mysql_params(self, url: str) -> dict:
        """Extract host/port/user/password/db from a SQLAlchemy-style MySQL URL."""
        clean = url.replace("mysql+pymysql://", "mysql://").replace("mysql+aiomysql://", "mysql://")
        parsed = urlparse(clean)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": parsed.username or "mcdr",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/") if parsed.path else "",
        }

    @property
    def core_db_params(self) -> dict:
        return self._parse_mysql_params(self.mcdr_core_db_url)

    @property
    def mobile_db_params(self) -> dict:
        return self._parse_mysql_params(self.mcdr_mobile_db_url)

    @property
    def cx_db_params(self) -> dict:
        return self._parse_mysql_params(self.mcdr_cx_db_url)

    @property
    def core_db_name(self) -> str:
        return self.core_db_params["database"]

    @property
    def mobile_db_name(self) -> str:
        return self.mobile_db_params["database"]

    @property
    def cx_db_name(self) -> str:
        return self.cx_db_params["database"]

    def validate_for_production(self) -> None:
        logger = logging.getLogger("mcdr")

        if self.is_production:
            if self.secret_key == _POC_SECRET or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not the default POC key. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if "localhost" in self.cors_origins or "127.0.0.1" in self.cors_origins:
                raise ValueError(
                    "CORS_ORIGINS must not contain localhost in production"
                )
            if self.access_token_expire_minutes > 60:
                logger.warning(
                    "ACCESS_TOKEN_EXPIRE_MINUTES=%d is > 60 min — consider shorter tokens with refresh",
                    self.access_token_expire_minutes,
                )
        elif self.environment != "development":
            if self.secret_key == _POC_SECRET:
                logger.warning(
                    "Using default POC secret key in %s — set SECRET_KEY env var",
                    self.environment,
                )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_for_production()
    return s
