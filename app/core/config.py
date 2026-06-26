from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    GROQ_API_KEY: str | None = None
    GOOGLE_SHEET_ID: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
