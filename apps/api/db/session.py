import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_DATABASE_URL = "postgresql+psycopg://cs2trade:cs2trade@localhost:5432/cs2trade"


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or _database_url())


engine = make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
