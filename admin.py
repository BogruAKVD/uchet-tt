from aiogram import Router, types, F
from aiogram.filters import Command, BaseFilter
from aiogram_dialog import DialogManager, StartMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from dialogs.create_position import create_position_dialog, CreatePositionState
from dialogs.create_project import CreateProjectState, create_project_dialog
from dialogs.create_task import CreateTaskState, create_task_dialog
from dialogs.create_worker import create_worker_dialog, CreateWorkerState
from dialogs.get_all_projects import get_all_projects_dialog, ProjectState
from dialogs.get_all_tasks import AllTasksState, get_all_tasks_dialog
from dialogs.edit_worker import edit_worker_dialog, EditWorkerState
from utils import is_admin

class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return is_admin(message.from_user.id)

async def show_main_keyboard(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать проект")],
            [KeyboardButton(text="Создать задачу")],
            [KeyboardButton(text="Создать сотрудника")],
            [KeyboardButton(text="Создать должность")],
            [KeyboardButton(text="Посмотреть все задачи")],
            [KeyboardButton(text="Посмотреть все проекты")],
            [KeyboardButton(text="Редактировать сотрудника")],
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
admin_router.include_router(create_worker_dialog())
admin_router.include_router(create_position_dialog())
admin_router.include_router(get_all_tasks_dialog())
admin_router.include_router(get_all_projects_dialog())
admin_router.include_router(edit_worker_dialog())


@admin_router.message(Command("start"))
async def start(message: types.Message, dialog_manager: DialogManager):
    await show_main_keyboard(message)

@admin_router.message(F.text == "Создать проект")
async def create_project_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateProjectState.name, mode=StartMode.RESET_STACK)


@admin_router.message(F.text == "Создать задачу")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateTaskState.name, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Создать сотрудника")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateWorkerState.name, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Создать должность")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreatePositionState.name, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Посмотреть все задачи")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(AllTasksState.show_tasks, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Посмотреть все проекты")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(ProjectState.list_projects, mode=StartMode.RESET_STACK)

@admin_router.message(F.text == "Редактировать сотрудника")
async def create_task_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(EditWorkerState.select_worker, mode=StartMode.RESET_STACK)
    
