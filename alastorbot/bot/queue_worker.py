"""
Background worker that periodically retries queued messages once
Gemini's quota may have freed up. Runs as a long-lived asyncio task
alongside the webhook server — not a separate process, since we're on
a single free-tier instance.
"""

import asyncio
import logging

from aiogram import Bot

from alastorbot.bot.response_service import generate_and_deliver_reply
from alastorbot.character.ai_client import QuotaExceededError
from alastorbot.database.engine import async_session_factory
from alastorbot.database.repositories import delete_pending_message, get_oldest_pending_messages
from alastorbot.database.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30 * 60  # every 30 minutes


async def process_pending_queue(bot: Bot) -> None:
    async with async_session_factory() as session:
        pending = await get_oldest_pending_messages(session, limit=5)

        for item in pending:
            user = await session.get(User, item.user_id)
            if user is None:
                await delete_pending_message(session, item.id)
                continue

            try:
                await generate_and_deliver_reply(
                    session, bot, user, item.chat_id, item.content
                )
                await delete_pending_message(session, item.id)
            except QuotaExceededError:
                # Quota's still exhausted — stop this cycle entirely,
                # the rest of the batch will fail too. Try again next
                # interval.
                logger.info("Quota still exhausted, pausing queue processing")
                return
            except Exception:
                logger.exception(f"Failed to process pending message {item.id}, will retry later")


async def run_queue_worker(bot: Bot) -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            await process_pending_queue(bot)
        except Exception:
            logger.exception("Queue worker cycle failed unexpectedly")