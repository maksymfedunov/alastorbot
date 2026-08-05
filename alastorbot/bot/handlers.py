from aiogram import Router
from aiogram.types import Message as TgMessage

from alastorbot.character.ai_client import gemini_answer
from alastorbot.database.engine import async_session_factory
from alastorbot.database.repositories import (
    get_or_create_user,
    get_recent_messages,
    get_user_memories,
    save_message,
)
from alastorbot.memory.memory_manager import extract_and_strip_memories, save_new_memories

router = Router()


@router.message()
async def handle_message(message: TgMessage) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )

        history = await get_recent_messages(session, user.id, limit=20)
        user_facts = await get_user_memories(session, user.id)

        raw_reply = await gemini_answer(
            user_message=message.text,
            history=history,
            user_facts=user_facts,
        )
        clean_reply, new_facts = extract_and_strip_memories(raw_reply)

        await save_message(session, user.id, role="user", content=message.text)
        await save_message(session, user.id, role="assistant", content=clean_reply)
        await save_new_memories(session, user.id, new_facts)

    await message.answer(clean_reply)