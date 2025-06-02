from typing import Any
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject
from data.database import Database
from message_sender import MessageSender
from notififcation_sender import NotificationSender


class NotificationSenderMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot, db: Database, message_sender: MessageSender):
        self.notification_sender = NotificationSender(bot, db, message_sender)

    async def startup(self):
        await self.notification_sender.start()

    async def __call__(
            self,
            handler,
            event: TelegramObject,
            data: dict,
    ) -> Any:
        data["notification_sender"] = self.notification_sender
        return await handler(event, data)