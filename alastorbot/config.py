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
