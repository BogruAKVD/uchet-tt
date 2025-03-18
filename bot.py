import asyncio
import os
import logging

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import Database

db = Database()

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers import admin, worker, common

load_dotenv()
# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


async def main():
    dp.include_router(admin.admin_router)
    dp.include_router(worker.worker_router)
    dp.include_router(common.common_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
