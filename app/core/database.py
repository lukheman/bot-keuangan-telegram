from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.base import Base

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

from sqlalchemy.pool import NullPool

# Buat async engine
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    poolclass=NullPool,
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
