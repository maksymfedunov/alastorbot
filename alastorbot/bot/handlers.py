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

WELCOME_MESSAGE = (
    "Итак, ты здесь. Осмелился заговорить с демоном — храбро, наивно, "
    "или и то, и другое сразу. Меня зовут Аластер Роули, и я, так уж "
    "вышло, заключаю сделки. Не спеши радоваться — я не подписываю "
    "контракты по первому требованию, но поговорить с тобой мне, "
    "пожалуй, будет забавно.\n\n"
    "Пара вещей, прежде чем мы начнём. У меня, как ни странно, есть "
    "пределы терпения даже для самых интересных собеседников — не "
    "больше десяти сообщений в день на одного. Не моя прихоть, "
    "поверь, просто мир не бесконечен, даже для меня.\n\n"
    "И если вдруг я замолчу дольше обычного — не думай, что сбежал "
    "или забыл о тебе. Демоны тоже бывают заняты: другие сделки, "
    "другие души, другие проблемы важнее твоих. Я вернусь, когда "
    "освобожусь, и твои слова никуда не денутся — просто наберись "
    "терпения, Фэр тебя дери.\n\n"
    "Итак. С чего начнём?"
)


@router.message(F.text)
async def handle_message(message: TgMessage) -> None:
    if message.text == "/start":
        await message.answer(WELCOME_MESSAGE)
        return

    if len(message.text) > MAX_MESSAGE_LENGTH:
        await message.answer(TOO_LONG_REPLY)
        return

    try:
        async with async_session_factory() as session:
            user, is_new = await get_or_create_user(
                session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )

            if is_new:
                await message.answer(WELCOME_MESSAGE)
                return

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