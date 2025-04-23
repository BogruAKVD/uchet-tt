from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import Database


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.db = db

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ) -> Any:
        data["db"] = self.db
        return await handler(event, data)