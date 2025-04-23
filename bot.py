import asyncio
import os
import logging

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram_dialog import setup_dialogs, DialogManager, StartMode
from dotenv import load_dotenv


from dialogs.create_project import create_project_dialog, CreateProjectState
from dialogs.db_middleware import DatabaseMiddleware

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

from aiogram import Bot, Dispatcher, types

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

from database import Database

db = Database()
# db.drop_all_tables()
db.create_tables()

from admin import admin_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

async def main():
    dp.update.outer_middleware(DatabaseMiddleware(db))
    dp.include_router(admin_router)
    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
