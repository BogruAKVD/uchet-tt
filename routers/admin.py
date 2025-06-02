from aiogram import Router, types, F
from aiogram.filters import Command, BaseFilter
from aiogram_dialog import DialogManager, StartMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from dialogs.admin.create_custom_task import create_custom_task_dialog, CreateCustomTaskState
from dialogs.admin.create_nonproject_task import CreateNonProjectTaskState, create_nonproject_task_dialog
from dialogs.admin.create_position import create_position_dialog, CreatePositionState
from dialogs.admin.create_project import CreateProjectState, create_project_dialog
from dialogs.admin.create_task import CreateTaskState, create_task_dialog
from dialogs.admin.create_worker import create_worker_dialog, CreateWorkerState
from dialogs.admin.edit_worker import edit_worker_dialog, EditWorkerState
from dialogs.admin.get_tables import get_tables_dialog, GetTablesState
from dialogs.admin.get_time_entries import get_time_entries_dialog, TimeEntryExportState
from dialogs.admin.send_message import send_message_dialog, SendMessageState
from utils import is_admin



class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return is_admin(message.from_user.id)

async def show_main_keyboard(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать проект")],
            [KeyboardButton(text="Создать задачу")],
            [KeyboardButton(text="Создать кастом")],
            [KeyboardButton(text="Создать непроектную задачу")],
            [KeyboardButton(text="Создать сотрудника")],
            [KeyboardButton(text="Создать должность")],
            [KeyboardButton(text="Редактировать сотрудника")],
            [KeyboardButton(text="Отправить сообщение")],
            [KeyboardButton(text="Получить таблицы")],
            [KeyboardButton(text="Получить таблицу учёта времени")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Выберите действие:",
        reply_markup=keyboard
    )


admin_router = Router()
admin_router.message.filter(AdminFilter())
admin_router.include_router(create_project_dialog())
admin_router.include_router(create_task_dialog())
admin_router.include_router(create_custom_task_dialog())
admin_router.include_router(create_nonproject_task_dialog())
admin_router.include_router(create_worker_dialog())
admin_router.include_router(create_position_dialog())
admin_router.include_router(edit_worker_dialog())
admin_router.include_router(send_message_dialog())
admin_router.include_router(get_tables_dialog())
admin_router.include_router(get_time_entries_dialog())


@admin_router.message(Command("start"))
async def start(message: types.Message, dialog_manager: DialogManager):
    await show_main_keyboard(message)

@admin_router.message(F.text == "Создать проект")
async def create_project_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateProjectState.name, mode=StartMode.RESET_STACK)


@admin_router.message(F.text == "Создать задачу")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateTaskState.name, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Создать кастом")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateCustomTaskState.select_font, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Создать непроектную задачу")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateNonProjectTaskState.select_department, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Создать сотрудника")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateWorkerState.name, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Создать должность")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreatePositionState.name, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Редактировать сотрудника")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(EditWorkerState.select_worker, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Отправить сообщение")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(SendMessageState.select_workers, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Получить таблицы")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(GetTablesState.main, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Получить таблицу учёта времени")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(TimeEntryExportState.main, mode=StartMode.RESET_STACK)

