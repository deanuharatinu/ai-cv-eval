from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
)

AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionMaker() as session:
        yield session


async def init_db() -> None:
    # Import models to ensure metadata is registered before creating tables.
    from app.infra import models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
