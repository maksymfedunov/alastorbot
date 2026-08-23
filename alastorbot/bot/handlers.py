import logging
import random

from aiogram import F, Router
from aiogram.types import Message as TgMessage

from alastorbot.character.ai_client import gemini_answer, QuotaExceededError
from alastorbot.bot.response_service import generate_and_deliver_reply
from alastorbot.database.engine import async_session_factory
from alastorbot.database.repositories import (
    DAILY_MESSAGE_LIMIT,
    check_and_increment_limit,
    enqueue_pending_message,
    get_or_create_user,
)
from alastorbot.memory.memory_manager import extract_and_strip_memories, save_new_memories

router = Router()
logger = logging.getLogger(__name__)

FALLBACK_REPLIES = [
    "...Хм. Похоже, связь между мирами сегодня барахлит — даже демонам иногда нужно перевести дух. Повтори через минуту?",
    "Что-то мешает мне тебя расслышать — будто помехи на линии между Адом и твоим миром. Попробуй ещё раз.",
    "Даже вечность иногда спотыкается. Дай мне момент и повтори вопрос.",
]

LIMIT_REACHED_REPLY = (
    f"Лимит сообщений на сегодня достигнут ({DAILY_MESSAGE_LIMIT}/{DAILY_MESSAGE_LIMIT}). "
    "Возвращайся завтра."
)

NON_TEXT_REPLY = "Слова, а не значки — вот что я понимаю. Скажи мне что-нибудь настоящее."

MAX_MESSAGE_LENGTH = 2000
TOO_LONG_REPLY = "Даже у моего терпения есть пределы — сократи мысль, и попробуем снова."

QUOTA_QUEUED_REPLY = (
    "Сегодня у меня иссякли силы говорить — слишком много желающих сделок сразу. "
    "Твоё слово я услышал и не забуду: отвечу, как только смогу перевести дух."
)


@router.message(F.text)
async def handle_message(message: TgMessage) -> None:
    if len(message.text) > MAX_MESSAGE_LENGTH:
        await message.answer(TOO_LONG_REPLY)
        return

    try:
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

            await message.bot.send_chat_action(message.chat.id, "typing")

            try:
                await generate_and_deliver_reply(
                    session, message.bot, user, message.chat.id, message.text
                )
            except QuotaExceededError:
                await enqueue_pending_message(session, user.id, message.chat.id, message.text)
                await message.answer(QUOTA_QUEUED_REPLY)
            except Exception:
                logger.exception("Error while calling the Gemini API")
                await message.answer(random.choice(FALLBACK_REPLIES))
    except Exception:
        logger.exception("Unexpected error while handling message")
        await message.answer(random.choice(FALLBACK_REPLIES))


@router.message()
async def handle_non_text(message: TgMessage) -> None:
    """Catches anything that didn't match F.text — stickers, photos, voice messages, etc."""
    await message.answer(NON_TEXT_REPLY)