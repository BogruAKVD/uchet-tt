from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject

from message_sender import MessageSender


class MessageSenderMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        self.message_sender = MessageSender(bot)

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ) -> Any:
        data["message_sender"] = self.message_sender
        return await handler(event, data)