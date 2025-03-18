from aiogram import Router, types, F
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext

from bot import db
from keyboards.common import add_cancel_button
from keyboards.worker import create_projects_keyboard, create_tasks_keyboard
from states import AddTimeEntry
from utils import is_worker, get_start_keyboard


class WorkerFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return is_worker(message.from_user.id)


worker_router = Router()
worker_router.message.filter(WorkerFilter())


# ===================== Add Time Entry Handlers =====================

@worker_router.message(F.text == "Внести время")
async def add_time_entry_command(message: types.Message, state: FSMContext):
    worker = db.get_worker_by_telegram_id(message.from_user.id)

    projects = db.get_worker_projects(worker['id'])
    if not projects:
        await message.answer("У вас нет назначенных проектов.", reply_markup=get_start_keyboard(message.from_user))
        return

    keyboard = create_projects_keyboard(projects)

    await message.answer("Выберите проект:", reply_markup=add_cancel_button(keyboard))
    await state.set_state(AddTimeEntry.choosing_project)


@worker_router.callback_query(AddTimeEntry.choosing_project, F.data.startswith("project:"))
async def project_chosen(query: types.CallbackQuery, state: FSMContext):
    project_id = int(query.data.split(":")[1])
    await state.update_data(project_id=project_id)

    worker = db.get_worker_by_telegram_id(query.from_user.id)
    tasks = db.get_worker_project_tasks(worker['id'], project_id)

    if not tasks:
        await query.message.answer("В этом проекте нет задач.", reply_markup=get_start_keyboard(query.from_user))
        await state.clear()
        return

    keyboard = create_tasks_keyboard(tasks)

    await query.message.edit_text("Выберите задачу:", reply_markup=add_cancel_button(keyboard))
    await state.set_state(AddTimeEntry.choosing_task)


@worker_router.callback_query(AddTimeEntry.choosing_task, F.data.startswith("task:"))
async def task_chosen(query: types.CallbackQuery, state: FSMContext):
    task_id = int(query.data.split(":")[1])
    await state.update_data(task_id=task_id)

    await query.message.edit_text("Введите время, потраченное на задачу в часах:", reply_markup=add_cancel_button())
    await state.set_state(AddTimeEntry.entering_time)


@worker_router.message(AddTimeEntry.entering_time)
async def time_entered(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text)
        if hours <= 0:
            await message.answer("Пожалуйста, введите положительное число (например 1.5). ", reply_markup=add_cancel_button())
            return
    except ValueError:
        await message.answer("Пожалуйста, введите число в формате 1.5", reply_markup=add_cancel_button())
        return

    data = await state.get_data()
    project_id = data.get("project_id")
    task_id = data.get("task_id")

    worker = db.get_worker_by_telegram_id(message.from_user.id)

    db.add_time_entry(project_id, worker['id'], task_id, hours)

    await message.answer(f"Время {hours} часов добавлено.", reply_markup=get_start_keyboard(message.from_user))
    await state.clear()
