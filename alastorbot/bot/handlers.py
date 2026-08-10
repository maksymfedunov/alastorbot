import logging
import random

from aiogram import F, Router
from aiogram.types import Message as TgMessage

from alastorbot.character.ai_client import gemini_answer
from alastorbot.database.engine import async_session_factory
from alastorbot.database.repositories import (
    DAILY_MESSAGE_LIMIT,
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

NON_TEXT_REPLY = "Слова, а не значки — вот что я понимаю. Скажи мне что-нибудь настоящее."

MAX_MESSAGE_LENGTH = 2000
TOO_LONG_REPLY = "Даже у моего терпения есть пределы — сократи мысль, и попробуем снова."

FALLBACK_REPLIES = [
    "...Хм. Похоже, связь между мирами сегодня барахлит — даже демонам иногда нужно перевести дух. Повтори через минуту?",
    "Что-то мешает мне тебя расслышать — будто помехи на линии между Адом и твоим миром. Попробуй ещё раз.",
    "Даже вечность иногда спотыкается. Дай мне момент и повтори вопрос.",
]

LIMIT_REACHED_REPLY = (
    f"Лимит сообщений на сегодня достигнут ({DAILY_MESSAGE_LIMIT}/{DAILY_MESSAGE_LIMIT}). "
    "Возвращайся завтра."
)


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

        history = await get_recent_messages(session, user.id, limit=20)
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
            logger.exception("Ошибка при обращении к Gemini API")
            await message.answer(random.choice(FALLBACK_REPLIES))
            return

        await save_message(session, user.id, role="user", content=message.text)
        await save_message(session, user.id, role="assistant", content=clean_reply)
        await save_new_memories(session, user.id, new_facts)
        await trim_old_messages(session, user.id)

    await message.answer(clean_reply)
    
    
@router.message()
async def handle_non_text(message: TgMessage) -> None:
    """Ловит всё, что не прошло фильтр F.text — стикеры, фото, голосовые и т.д."""
    await message.answer(NON_TEXT_REPLY)    