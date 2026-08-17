import logging
import random

from aiogram import F, Router
from aiogram.types import Message as TgMessage

from alastorbot.character.ai_client import gemini_answer
from alastorbot.database.engine import async_session_factory
from alastorbot.database.repositories import (
    DAILY_MESSAGE_LIMIT,
    HISTORY_LIMIT,
    check_and_increment_limit,
    get_or_create_user,
    get_recent_messages,
    get_user_memories,
    save_message,
    trim_old_messages,
)
from alastorbot.memory.memory_manager import extract_and_strip_memories, save_new_memories

router = Router()
logger = logging.getLogger(__name__)

FALLBACK_REPLIES = [
    "...Hmm. Seems the connection between worlds is glitching today — even demons need to catch their breath sometimes. Try again in a minute?",
    "Something's interfering with hearing you — like static on the line between Hell and your world. Try again.",
    "Even eternity stumbles sometimes. Give me a moment and repeat the question.",
]

LIMIT_REACHED_REPLY = (
    f"Daily message limit reached ({DAILY_MESSAGE_LIMIT}/{DAILY_MESSAGE_LIMIT}). "
    "Come back tomorrow."
)

NON_TEXT_REPLY = "Words, not little icons — that's what I understand. Tell me something real."

MAX_MESSAGE_LENGTH = 2000
TOO_LONG_REPLY = "Even my patience has limits — trim that thought down, and let's try again."


@router.message(F.text)
async def handle_message(message: TgMessage) -> None:
    if len(message.text) > MAX_MESSAGE_LENGTH:
        await message.answer(TOO_LONG_REPLY)
        return

    async with async_session_factory() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )

        allowed = await check_and_increment_limit(session, user)
        if not allowed:
            await message.answer(LIMIT_REACHED_REPLY)
            return

        history = await get_recent_messages(session, user.id, limit=HISTORY_LIMIT)
        user_facts = await get_user_memories(session, user.id)

        await message.bot.send_chat_action(message.chat.id, "typing")

        try:
            raw_reply = await gemini_answer(
                user_message=message.text,
                history=history,
                user_facts=user_facts,
            )
            clean_reply, new_facts = extract_and_strip_memories(raw_reply)
        except Exception:
            logger.exception("Error while calling the Gemini API")
            await message.answer(random.choice(FALLBACK_REPLIES))
            return

        await save_message(session, user.id, role="user", content=message.text)
        await save_message(session, user.id, role="assistant", content=clean_reply)
        await save_new_memories(session, user.id, new_facts)
        await trim_old_messages(session, user.id)

    await message.answer(clean_reply)


@router.message()
async def handle_non_text(message: TgMessage) -> None:
    """Catches anything that didn't match F.text — stickers, photos, voice messages, etc."""
    await message.answer(NON_TEXT_REPLY)