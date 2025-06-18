from aiogram import Router, types, F
from aiogram.filters import Command, BaseFilter
from aiogram_dialog import DialogManager
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from dialogs.worker.create_time_entry import TimeEntryStates, create_time_entry_dialog
from dialogs.worker.edit_reminder_settings import edit_reminder_settings_dialog, ReminderSettingsStates
from dialogs.worker.export_time_table import export_time_table_dialog, ExportTimeTableStates
from dialogs.worker.import_time_table import import_time_table_dialog, ImportTimeTableStates
from dialogs.worker.select_projects import select_projects_dialog, ProjectSelectStates
from dialogs.worker.view_time_entry import ViewTimeEntriesStates, view_time_entries_dialog

from utils import is_worker


class WorkerFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return is_worker(message.from_user.id)


async def show_main_keyboard(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить время")],
            [KeyboardButton(text="Изменить активные проекты")],
            [KeyboardButton(text="Изменить напоминания")],
            [KeyboardButton(text="Просмотреть записи")],
            [KeyboardButton(text="Экспортировать таблицу")],
            [KeyboardButton(text="Импортировать таблицу")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Выберите действие:",
        reply_markup=keyboard
    )


worker_router = Router()
worker_router.message.filter(WorkerFilter())
worker_router.include_router(create_time_entry_dialog())
worker_router.include_router(select_projects_dialog())
worker_router.include_router(edit_reminder_settings_dialog())
worker_router.include_router(view_time_entries_dialog())
worker_router.include_router(export_time_table_dialog())
worker_router.include_router(import_time_table_dialog())

@worker_router.message(Command("start"))
async def start(message: types.Message, dialog_manager: DialogManager):
    await show_main_keyboard(message)


@worker_router.message(F.text == "Добавить время")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(TimeEntryStates.select_project)

@worker_router.message(F.text == "Изменить активные проекты")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(ProjectSelectStates.select_projects)

@worker_router.message(F.text == "Изменить напоминания")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(ReminderSettingsStates.select_day)

@worker_router.message(F.text == "Просмотреть записи")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(ViewTimeEntriesStates.select_period)

@worker_router.message(F.text == "Экспортировать таблицу")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(ExportTimeTableStates.processing)

@worker_router.message(F.text == "Импортировать таблицу")
async def add_time_button(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(ImportTimeTableStates.upload)
