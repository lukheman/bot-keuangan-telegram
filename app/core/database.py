from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.base import Base

# Gunakan aiosqlite untuk async SQLite
DATABASE_URL = "sqlite+aiosqlite:///./finance_bot.db"

# Buat async engine
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
)

# Factory untuk membuat async session
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Helper function untuk dependency injection session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
