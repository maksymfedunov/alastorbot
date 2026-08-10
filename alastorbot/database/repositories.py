from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from alastorbot.database.models import Message, User, UserMemory

DAILY_MESSAGE_LIMIT = 10
HISTORY_LIMIT = 20


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
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


async def trim_old_messages(session: AsyncSession, user_id: int, keep_last: int = HISTORY_LIMIT) -> None:
    """
    Удаляет сообщения пользователя старше последних keep_last —
    храним ровно столько, сколько реально читается get_recent_messages,
    остальное никогда больше не используется.
    """
    result = await session.execute(
        select(Message.id)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .offset(keep_last)
    )
    old_ids = [row[0] for row in result.all()]

    if old_ids:
        await session.execute(delete(Message).where(Message.id.in_(old_ids)))
        await session.commit()


async def get_recent_messages(session: AsyncSession, user_id: int, limit: int = HISTORY_LIMIT) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


async def check_and_increment_limit(session: AsyncSession, user: User) -> bool:
    today = date.today()

    stored_reset_date = user.limit_reset_date
    if isinstance(stored_reset_date, datetime):
        stored_reset_date = stored_reset_date.date()

    if stored_reset_date != today:
        user.messages_today = 0
        user.limit_reset_date = today

    if user.messages_today >= DAILY_MESSAGE_LIMIT:
        await session.commit()
        return False

    user.messages_today += 1
    await session.commit()
    return True


async def save_memory_fact(session: AsyncSession, user_id: int, fact: str) -> None:
    session.add(UserMemory(user_id=user_id, fact=fact))
    await session.commit()


async def get_user_memories(session: AsyncSession, user_id: int) -> list[UserMemory]:
    result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    return list(result.scalars().all())