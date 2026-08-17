"""
Application settings.

All environment-dependent parameters (tokens, keys, paths) are read
only here — via pydantic-settings from the .env file. The rest of the
code imports the ready-made `settings` object instead of reading
environment variables directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    GEMINI_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///data/alastorbot.db"
    WEBHOOK_BASE_URL: str
    WEBHOOK_SECRET: str
    PORT: int = 8080

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
