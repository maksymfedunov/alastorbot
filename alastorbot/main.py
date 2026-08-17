import logging

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from alastorbot.bot import router
from alastorbot.config import settings

WEBHOOK_PATH = "/webhook"


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(
        url=f"{settings.WEBHOOK_BASE_URL}{WEBHOOK_PATH}",
        secret_token=settings.WEBHOOK_SECRET,
    )


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