from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    GROQ_API_KEY: str | None = None
    GOOGLE_SHEET_ID: str | None = None
    WEBHOOK_URL: str | None = None
    PORT: int = 8443
    GOOGLE_SHEETS_CREDENTIALS_B64: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./finance_bot.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"

settings = Settings()
