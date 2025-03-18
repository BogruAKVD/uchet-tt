import os

from aiogram.types import User, ReplyKeyboardMarkup

from bot import db
from keyboards.admin import admin_keyboard
from keyboards.worker import worker_keyboard

ADMIN_ID = int(os.getenv("ADMIN_ID"))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def is_worker(user_id: int) -> bool:
    return db.get_worker_by_telegram_id(telegram_id=user_id) is not None

def get_start_keyboard(user: User):
    match (is_admin(user.id), is_worker(user.id)):
        case (True, True):
            admin_worker_keyboard = ReplyKeyboardMarkup(
                keyboard=admin_keyboard().keyboard + worker_keyboard().keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
            return admin_worker_keyboard
        case (True, False):
            return admin_keyboard()
        case (False, True):
            return worker_keyboard()
        case (False, False):
            return None
