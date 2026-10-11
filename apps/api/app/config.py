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
    # The daily task and the provider's notices connect as `arrendi_tasks`.
    database_url_tasks: str = ""
    # Email; see app/email/sender.py.
    email_api_key: str = ""
    email_sender: str = ""
    # While set, every email goes to this inbox instead of to the tenant.
    email_test_inbox: str = ""
    email_webhook_secret: str = ""
    cron_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
