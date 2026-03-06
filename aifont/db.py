"""SQLAlchemy async database engine and session factory."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://aifont:aifont@localhost:5432/aifont",
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
