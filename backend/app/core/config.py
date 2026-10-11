from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CMDB_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cmdb:cmdb@localhost:5432/cmdb"

    # OIDC
    oidc_issuer: str = "http://localhost:8080/realms/cmdb"
    oidc_audience: str = "cmdb-api"
    oidc_roles_claim: str = "roles"
    # Если IdP недоступен бэкенду по адресу issuer (напр. внутри docker-сети)
    oidc_jwks_url: str | None = None
    # Отключает проверку токена — только для локальной разработки и тестов
    auth_disabled: bool = False

    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
