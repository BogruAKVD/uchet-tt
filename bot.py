import asyncio
import os
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_dialog import setup_dialogs

from data.database import db
from middlewares.database_middleware import DatabaseMiddleware
from middlewares.message_sender_middleware import MessageSenderMiddleware
from middlewares.notification_sender_middleware import NotificationSenderMiddleware
from routers.admin import admin_router
from routers.worker import worker_router
from routers.default import default_router


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


async def main():
    setup_logging()

    database_middleware = DatabaseMiddleware(db)
    message_sender_middleware = MessageSenderMiddleware(bot)
    notification_sender_middleware = NotificationSenderMiddleware(bot, database_middleware.db, message_sender_middleware.message_sender)
    await notification_sender_middleware.startup()

    dp.update.outer_middleware(database_middleware)
    dp.update.outer_middleware(message_sender_middleware)
    dp.update.outer_middleware(notification_sender_middleware)

    dp.include_router(admin_router)
    dp.include_router(worker_router)
    dp.include_router(default_router)

    setup_dialogs(dp)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot stopped with error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
