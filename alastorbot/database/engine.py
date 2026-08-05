from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alastorbot.config import settings

engine = create_async_engine(settings.DATABASE_URL)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession: # type: ignore
    async with async_session_factory() as session:
        yield session