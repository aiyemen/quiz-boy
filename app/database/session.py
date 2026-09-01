"""
Database session management for QuizBot Arabic.
Supports async engine via SQLAlchemy async / SQLite / PostgreSQL.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config.settings import settings
from app.database.models import Base

# Ensure SQLite URL is properly formatted for async
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg:///")

engine = create_async_engine(
    db_url,
    echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency / context manager for async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables for dev/testing if not using alembic directly."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close engine connections gracefully."""
    await engine.dispose()
