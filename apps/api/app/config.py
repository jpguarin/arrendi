from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "preview", "production"] = "local"
    database_url: str = ""
    database_url_migrations: str = ""
    supabase_url: str = ""
    # Only for file storage; see app/storage.py.
    supabase_secret_key: str = ""
    storage_bucket: str = "arrendi"


@lru_cache
def get_settings() -> Settings:
    return Settings()
