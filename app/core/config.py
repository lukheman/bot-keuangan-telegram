from pydantic_settings import BaseSettings
from pydantic import field_validator

import os

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
            
            # Clean up asyncpg unsupported query parameters
            if "?" in v:
                from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
                parsed = urlparse(v)
                if parsed.query:
                    qs = parse_qsl(parsed.query)
                    new_qs = []
                    for key, val in qs:
                        if key == "sslmode":
                            new_qs.append(("ssl", val))
                        elif key == "channel_binding":
                            continue # asyncpg doesn't support this
                        else:
                            new_qs.append((key, val))
                    parsed = parsed._replace(query=urlencode(new_qs))
                    v = urlunparse(parsed)
        return v

    class Config:
        env_file = os.getenv("ENV_FILE", ".env")
        env_file_encoding = 'utf-8'

settings = Settings()
