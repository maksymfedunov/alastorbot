from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from alastorbot.database.models import Message, User, UserMemory, PendingMessage

DAILY_MESSAGE_LIMIT = 10
HISTORY_LIMIT = 20


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> tuple[User, bool]:
    """
    Returns the user and whether they were just created — the caller
    uses this to decide whether to show the first-time welcome message
    instead of processing this message as a normal reply.
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True
    return user, False


async def save_message(session: AsyncSession, user_id: int, role: str, content: str) -> None:
    session.add(Message(user_id=user_id, role=role, content=content))
    await session.commit()


async def trim_old_messages(session: AsyncSession, user_id: int, keep_last: int = HISTORY_LIMIT) -> None:
    """
    Deletes messages older than the last keep_last for the given user —
    we only keep as many as get_recent_messages actually reads, since
    anything older is never used again.
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
    messages.reverse()  # back to chronological order
    return messages


async def check_and_increment_limit(session: AsyncSession, user: User) -> bool:
    """
    Checks the user's daily message limit. Returns True if the message
    is allowed (and immediately increments the counter), False if
    today's limit has been reached.
    """
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


async def enqueue_pending_message(session: AsyncSession, user_id: int, chat_id: int, content: str) -> None:
    session.add(PendingMessage(user_id=user_id, chat_id=chat_id, content=content))
    await session.commit()


async def get_oldest_pending_messages(session: AsyncSession, limit: int = 5) -> list[PendingMessage]:
    """
    Returns the oldest queued messages first (FIFO) — so whoever
    waited longest gets answered first once quota is available again.
    """
    result = await session.execute(
        select(PendingMessage).order_by(PendingMessage.created_at.asc()).limit(limit)
    )
    return list(result.scalars().all())


async def delete_pending_message(session: AsyncSession, pending_id: int) -> None:
    await session.execute(delete(PendingMessage).where(PendingMessage.id == pending_id))
    await session.commit()