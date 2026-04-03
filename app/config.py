from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Finance Data Processing and Access Control Backend"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True

    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str

    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str | None

    secret_key: str = "replace-with-strong-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    admin_bootstrap_key: str | None = None

    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 100
    sensitive_rate_limit_window_seconds: int = 60
    sensitive_rate_limit_max_requests: int = 20

    heartbeat_interval_seconds: int = 15
    online_status_ttl_seconds: int = 45

    dashboard_cache_ttl_seconds: int = 60
    recycle_bin_retention_days: int = 30
    max_csv_import_bytes: int = 5 * 1024 * 1024
    jwt_clock_skew_seconds: int = 10

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return (
                "redis://"
                f":{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
