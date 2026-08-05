from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alastorbot.database.models import Message, User, UserMemory


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def save_message(session: AsyncSession, user_id: int, role: str, content: str) -> None:
    session.add(Message(user_id=user_id, role=role, content=content))
    await session.commit()


async def get_recent_messages(session: AsyncSession, user_id: int, limit: int = 20) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # обратно в хронологический порядок
    return messages


async def save_memory_fact(session: AsyncSession, user_id: int, fact: str) -> None:
    session.add(UserMemory(user_id=user_id, fact=fact))
    await session.commit()


async def get_user_memories(session: AsyncSession, user_id: int) -> list[UserMemory]:
    result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    return list(result.scalars().all())