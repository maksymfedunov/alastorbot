"""
Application entry point.

Sets up the Telegram bot with a webhook (instead of polling) so it
can run on a hosting platform without keeping a terminal open.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from alastorbot.bot.queue_worker import run_queue_worker
from alastorbot.bot import router
from alastorbot.config import settings

WEBHOOK_PATH = "/webhook"




async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(
        url=f"{settings.WEBHOOK_BASE_URL}{WEBHOOK_PATH}",
        secret_token=settings.WEBHOOK_SECRET,
    )
    asyncio.create_task(run_queue_worker(bot))


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=settings.PORT)


if __name__ == "__main__":
    main()