"""Application settings, read from the repo-root .env via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> app -> backend -> repo root. Resolved from __file__ rather than the
# working directory so uvicorn, pytest and `python -c ...` all find the same .env.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    jwt_expire_hours: int = 12
    llm_api_key: str = ""
    llm_provider: str = "gemini"


settings = Settings()
