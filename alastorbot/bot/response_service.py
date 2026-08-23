"""
Shared logic for generating and delivering a character reply — used
both by the live message handler and by the background queue worker,
so the two paths stay in sync instead of duplicating the same steps.
"""

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from alastorbot.character.ai_client import gemini_answer
from alastorbot.database.models import User
from alastorbot.database.repositories import (
    HISTORY_LIMIT,
    get_recent_messages,
    get_user_memories,
    save_message,
    trim_old_messages,
)
from alastorbot.memory.memory_manager import extract_and_strip_memories, save_new_memories

async def generate_and_deliver_reply(
    session: AsyncSession,
    bot: Bot,
    user: User,
    chat_id: int,
    user_message: str,
) -> None:
    """
    Calls Gemini, saves the exchange to history/memory, and sends the
    reply to the given chat. Raises QuotaExceededError or other
    exceptions to the caller — this function does not swallow errors,
    each caller decides how to react (fallback reply vs. re-queue).
    """
    history = await get_recent_messages(session, user.id, limit=HISTORY_LIMIT)
    user_facts = await get_user_memories(session, user.id)

    raw_reply = await gemini_answer(
        user_message=user_message,
        history=history,
        user_facts=user_facts,
    )
    clean_reply, new_facts = extract_and_strip_memories(raw_reply)

    await save_message(session, user.id, role="user", content=user_message)
    await save_message(session, user.id, role="assistant", content=clean_reply)
    await save_new_memories(session, user.id, new_facts)
    await trim_old_messages(session, user.id)

    await bot.send_message(chat_id, clean_reply)