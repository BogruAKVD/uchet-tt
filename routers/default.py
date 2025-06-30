import logging

from aiogram import Router, types, F
from aiogram.filters import Command, BaseFilter
from aiogram_dialog import DialogManager, StartMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils import is_admin, is_worker


class DefaultFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return not is_admin(message.from_user.id) and not is_worker(message.from_user.id)





default_router = Router()

@default_router.message()
async def start(message: types.Message, dialog_manager: DialogManager):
    logging.info(f"User {message.from_user.id} постучался")
    await message.answer("Извините, но вы не являетесь сотрудником или администратором. "
                         "Если вам нужен доступ к системе, пожалуйста, обратитесь к администратору.")

