from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ApplicationConfig(BaseConfig):
    host: str = Field(alias="APP_HOST", default="0.0.0.0")
    port: int = Field(alias="APP_PORT", default=8000, ge=1, le=65535)
    reload: bool = Field(alias="APP_RELOAD", default=False)
    webhook_secret: str = Field(alias="WEBHOOK_SECRET", min_length=1)


class DatabaseConfig(BaseConfig):
    host: str = Field(alias="DATABASE_HOST", default="localhost")
    port: int = Field(alias="DATABASE_PORT", default=5432, ge=1, le=65535)
    username: str = Field(alias="DATABASE_USERNAME", default="payment_service")
    password: str = Field(alias="DATABASE_PASSWORD")
    name: str = Field(alias="DATABASE_NAME", default="payment_service")

    @property
    def url(self) -> str:
        return URL.create(
            "postgresql+asyncpg",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        ).render_as_string(hide_password=False)


class Settings:
    def __init__(self) -> None:
        self.app = ApplicationConfig()
        self.database = DatabaseConfig()


@lru_cache
def get_settings() -> Settings:
    return Settings()
