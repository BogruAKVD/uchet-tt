from aiogram import Router, types, F
from aiogram.filters import Command, BaseFilter
from aiogram_dialog import DialogManager, StartMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from dialogs import add_time
from dialogs.add_time import TimeEntryStates
from utils import is_worker


class WorkerFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return is_worker(message.from_user.id)


async def show_main_keyboard(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить время")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Выберите действие:",
        reply_markup=keyboard
    )

worker_router = Router()



@worker_router.message(Command("start"))
async def start(message: types.Message, dialog_manager: DialogManager):
    await show_main_keyboard(message)


@worker_router.message(F.text == "Добавить время")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(TimeEntryStates.select_project)

