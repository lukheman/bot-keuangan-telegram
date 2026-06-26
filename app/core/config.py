from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    GROQ_API_KEY: str | None = None
    GOOGLE_SHEET_ID: str | None = None
    WEBHOOK_URL: str | None = None
    PORT: int = 8443

    class Config:
        env_file = ".env"

settings = Settings()
