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
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # Fix asyncpg sslmode issue
            if "sslmode=" in v:
                v = v.replace("sslmode=", "ssl=")
        return v

    class Config:
        env_file = ".env"

settings = Settings()
