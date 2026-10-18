from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = Field(repr=False)
    JWT_SECRET_KEY: str = Field(repr=False)
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = Field(default=2, gt=0, le=168)
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = Field(default=None, repr=False)
    APP_ENV: Literal["development", "test", "production"] = "production"
    ENABLE_SIMULATED_PAYMENTS: bool = False
    DEFAULT_PAGE_SIZE: int = Field(default=20, ge=1, le=100)
    MAX_PAGE_SIZE: int = Field(default=100, ge=1, le=100)
    PASSWORD_MAX_UTF8_BYTES: int = 72

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


config = Settings()
