from aiogram import types, Router, F
from aiogram.filters import StateFilter, BaseFilter
from aiogram.fsm.context import FSMContext

from bot import db
from keyboards.admin import *
from keyboards.common import add_cancel_button
from states import AddProject, EditProject, AddTaskType, AddWorker
from database import ProjectType
from utils import is_admin, get_start_keyboard


class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return is_admin(message.from_user.id)


admin_router = Router()
admin_router.message.filter(AdminFilter())


# ===================== Add Project Handlers =====================
@admin_router.message(F.text == "Добавить проект")
async def add_project_command(message: types.Message, state: FSMContext):
    await state.set_state(AddProject.name)
    await message.answer("Введите название проекта:", reply_markup=add_cancel_button())


@admin_router.message(StateFilter(AddProject.name))
async def add_project_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProject.project_type)
    await message.answer("Выберите тип проекта:", reply_markup=add_cancel_button(project_type_keyboard()))


@admin_router.callback_query(StateFilter(AddProject.project_type), F.data.startswith("project_type:"))
async def add_project_type(query: types.CallbackQuery, state: FSMContext):
    project_type = query.data.split(":")[1]
    await state.update_data(project_type=project_type)
    await state.set_state(AddProject.tasks)

    all_tasks = db.get_all_tasks()
    if not all_tasks:
        await query.message.answer("Нет доступных задач. Сначала добавьте задачи.",
                                   reply_markup=add_cancel_button())
        await state.clear()
        return

    task_keyboard = create_task_keyboard(all_tasks)
    await query.message.answer("Выберите задачи для проекта:", reply_markup=add_cancel_button(task_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(AddProject.tasks), F.data.startswith("task:"))
async def add_project_task_select(query: types.CallbackQuery, state: FSMContext):
    callback_data = query.data.split(":")
    task_id = int(callback_data[1])
    selected = int(callback_data[2])

    state_data = await state.get_data()
    selected_tasks = state_data.get("selected_tasks", {})

    selected_tasks[task_id] = not bool(selected)

    await state.update_data(selected_tasks=selected_tasks)

    all_tasks = db.get_all_tasks()
    task_keyboard = create_task_keyboard(all_tasks, selected_tasks)
    await query.message.edit_reply_markup(reply_markup=add_cancel_button(task_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(AddProject.tasks), F.data == "tasks:confirm")
async def add_project_tasks_confirm(query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    selected_tasks = state_data.get("selected_tasks", {})

    task_ids = [task_id for task_id, selected in selected_tasks.items() if selected]

    await state.update_data(task_ids=task_ids)
    await state.set_state(AddProject.workers)

    all_workers = db.get_all_workers()
    if not all_workers:
        await query.message.answer("Нет доступных сотрудников. Сначала добавьте сотрудников.",
                                   reply_markup=add_cancel_button())
        await state.clear()
        return

    worker_keyboard = create_worker_keyboard(all_workers)
    await query.message.answer("Выберите сотрудников для проекта:", reply_markup=add_cancel_button(worker_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(AddProject.workers), F.data.startswith("worker:"))
async def add_project_worker_select(query: types.CallbackQuery, state: FSMContext):
    callback_data = query.data.split(":")
    worker_id = int(callback_data[1])
    selected = int(callback_data[2])

    state_data = await state.get_data()
    selected_workers = state_data.get("selected_workers", {})

    selected_workers[worker_id] = not bool(selected)

    await state.update_data(selected_workers=selected_workers)

    all_workers = db.get_all_workers()
    worker_keyboard = create_worker_keyboard(all_workers, selected_workers)
    await query.message.edit_reply_markup(reply_markup=add_cancel_button(worker_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(AddProject.workers), F.data == "workers:confirm")
async def add_project_workers_confirm(query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    selected_workers = state_data.get("selected_workers", {})

    worker_ids = [worker_id for worker_id, selected in selected_workers.items() if selected]

    await state.update_data(worker_ids=worker_ids)
    await state.set_state(AddProject.confirm)

    project_data = await state.get_data()
    project_name = project_data.get("name")
    project_type = project_data.get("project_type")
    task_ids = project_data.get("task_ids")
    worker_ids = project_data.get("worker_ids")
    task_names = db.get_task_names(task_ids)
    worker_names = db.get_worker_names(worker_ids)

    message_text = f"<b>Подтвердите создание проекта:</b>\n"
    message_text += f"<b>Название:</b> {project_name}\n"
    message_text += f"<b>Тип:</b> {project_type}\n"
    message_text += f"<b>Задачи:</b> {', '.join(task_names)}\n"
    message_text += f"<b>Сотрудники:</b> {', '.join(worker_names)}\n"

    await query.message.answer(message_text, reply_markup=add_cancel_button(confirm_keyboard()))
    await query.answer()


@admin_router.callback_query(StateFilter(AddProject.confirm), F.data == "confirm")
async def add_project_confirm(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    project_name = data["name"]
    project_type = data["project_type"]
    task_ids = data["task_ids"]
    worker_ids = data["worker_ids"]

    project_type_enum = getattr(ProjectType, project_type.upper())
    db.create_project(project_name, project_type_enum, task_ids, worker_ids)
    await query.message.answer("Проект успешно создан!", reply_markup=get_start_keyboard(query.from_user))
    await state.clear()
    await query.answer()


# ===================== Edit Project Handlers =====================
@admin_router.message(F.text == "Редактировать проект")
async def edit_project_command(message: types.Message, state: FSMContext):
    await state.set_state(EditProject.project_select)

    projects = db.get_all_projects()
    if not projects:
        await message.answer("Нет доступных проектов.")
        await state.clear()
        return

    project_keyboard = create_project_keyboard(projects)
    await message.answer("Выберите проект для редактирования:", reply_markup=add_cancel_button(project_keyboard))


@admin_router.callback_query(StateFilter(EditProject.project_select), F.data.startswith("project:"))
async def edit_project_select(query: types.CallbackQuery, state: FSMContext):
    project_id = int(query.data.split(":")[1])

    project = db.get_project(project_id)

    await state.update_data(project_id=project_id)
    await state.set_state(EditProject.action_select)

    project_tasks = db.get_project_tasks(project_id)
    task_names = [task['name'] for task in project_tasks]

    project_workers = db.get_project_workers(project_id)
    worker_names = [worker['name'] for worker in project_workers]

    message_text = f"<b>Редактирование проекта:</b>\n"
    message_text += f"<b>Название:</b> {project['name']}\n"
    message_text += f"<b>Тип:</b> {project['type']}\n"
    message_text += f"<b>Задачи:</b> {', '.join(task_names)}\n"
    message_text += f"<b>Сотрудники:</b> {', '.join(worker_names)}\n"

    edit_keyboard = create_edit_keyboard()
    await query.message.answer(message_text, reply_markup=add_cancel_button(edit_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(EditProject.action_select), F.data.startswith("edit:"))
async def edit_project_action(query: types.CallbackQuery, state: FSMContext):
    action = query.data.split(":")[1]
    await state.update_data(action=action)

    if action == "name":
        await state.set_state(EditProject.new_name)
        await query.message.answer("Введите новое название проекта:",
                                   reply_markup=add_cancel_button())
    elif action == "type":
        await state.set_state(EditProject.new_type)
        await query.message.answer("Выберите новый тип проекта:",
                                   reply_markup=add_cancel_button(project_type_keyboard()))
    elif action == "tasks":
        await state.set_state(EditProject.new_tasks)
        project_id = (await state.get_data()).get("project_id")
        all_tasks = db.get_all_tasks()
        project_tasks = db.get_project_tasks(project_id)
        selected_tasks = {task['id']: True for task in project_tasks}
        await state.update_data(selected_tasks=selected_tasks)
        task_keyboard = create_task_keyboard(all_tasks, selected_tasks)
        await query.message.answer("Выберите новые задачи для проекта:", reply_markup=add_cancel_button(task_keyboard))
    elif action == "workers":
        await state.set_state(EditProject.new_workers)
        project_id = (await state.get_data()).get("project_id")
        all_workers = db.get_all_workers()
        project_workers = db.get_project_workers(project_id)
        selected_workers = {worker['id']: True for worker in project_workers}
        await state.update_data(selected_workers=selected_workers)
        worker_keyboard = create_worker_keyboard(all_workers, selected_workers)
        await query.message.answer("Выберите новых сотрудников для проекта:",
                                   reply_markup=add_cancel_button(worker_keyboard))
    await query.answer()


@admin_router.message(StateFilter(EditProject.new_name))
async def edit_project_new_name(message: types.Message, state: FSMContext):
    new_name = message.text
    await state.update_data(new_name=new_name)
    await state.set_state(EditProject.confirm)
    await message.answer(f"Вы уверены, что хотите изменить название проекта на '{new_name}'?",
                         reply_markup=add_cancel_button(confirm_keyboard()))


@admin_router.callback_query(StateFilter(EditProject.new_type), F.data.startswith("project_type:"))
async def edit_project_new_type(query: types.CallbackQuery, state: FSMContext):
    new_type = query.data.split(":")[1]
    await state.update_data(new_type=new_type)
    await state.set_state(EditProject.confirm)
    await query.message.answer(f"Вы уверены, что хотите изменить тип проекта на '{new_type}'?",
                               reply_markup=add_cancel_button(confirm_keyboard()))
    await query.answer()


@admin_router.callback_query(StateFilter(EditProject.new_tasks), F.data.startswith("task:"))
async def edit_project_new_task_select(query: types.CallbackQuery, state: FSMContext):
    callback_data = query.data.split(":")
    task_id = int(callback_data[1])
    selected = int(callback_data[2])

    state_data = await state.get_data()
    selected_tasks = state_data.get("selected_tasks", {})

    selected_tasks[task_id] = not bool(selected)

    await state.update_data(selected_tasks=selected_tasks)

    all_tasks = db.get_all_tasks()
    task_keyboard = create_task_keyboard(all_tasks, selected_tasks)
    await query.message.edit_reply_markup(reply_markup=add_cancel_button(task_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(EditProject.new_tasks), F.data == "tasks:confirm")
async def edit_project_new_tasks_confirm(query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    selected_tasks = state_data.get("selected_tasks", {})

    task_ids = [task_id for task_id, selected in selected_tasks.items() if selected]

    await state.update_data(new_tasks=task_ids)
    await state.set_state(EditProject.confirm)
    await query.message.answer("Вы уверены, что хотите изменить задачи проекта?",
                               reply_markup=add_cancel_button(confirm_keyboard()))
    await query.answer()


@admin_router.callback_query(StateFilter(EditProject.new_workers), F.data.startswith("worker:"))
async def edit_project_new_worker_select(query: types.CallbackQuery, state: FSMContext):
    callback_data = query.data.split(":")
    worker_id = int(callback_data[1])
    selected = int(callback_data[2])

    state_data = await state.get_data()
    selected_workers = state_data.get("selected_workers", {})

    selected_workers[worker_id] = not bool(selected)

    await state.update_data(selected_workers=selected_workers)

    all_workers = db.get_all_workers()
    worker_keyboard = create_worker_keyboard(all_workers, selected_workers)
    await query.message.edit_reply_markup(reply_markup=add_cancel_button(worker_keyboard))
    await query.answer()


@admin_router.callback_query(StateFilter(EditProject.new_workers), F.data == "workers:confirm")
async def edit_project_new_workers_confirm(query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    selected_workers = state_data.get("selected_workers", {})

    worker_ids = [worker_id for worker_id, selected in selected_workers.items() if selected]

    await state.update_data(new_workers=worker_ids)
    await state.set_state(EditProject.confirm)
    await query.message.answer("Вы уверены, что хотите изменить сотрудников проекта?",
                               reply_markup=add_cancel_button(confirm_keyboard()))
    await query.answer()


@admin_router.callback_query(StateFilter(EditProject.confirm), F.data == "confirm")
async def edit_project_confirm(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    project_id = data["project_id"]
    action = data["action"]

    if action == "name":
        new_name = data["new_name"]
        db.update_project(project_id, new_name=new_name)
        await query.message.answer("Название проекта успешно изменено!",
                                   reply_markup=get_start_keyboard(query.from_user))
    elif action == "type":
        new_type = data["new_type"]
        project_type_enum = getattr(ProjectType, new_type.upper())
        db.update_project(project_id, new_type=project_type_enum)
        await query.message.answer("Тип проекта успешно изменен!", reply_markup=get_start_keyboard(query.from_user))
    elif action == "tasks":
        new_tasks = data["new_tasks"]
        db.update_project(project_id, new_tasks=new_tasks)
        await query.message.answer("Задачи проекта успешно изменены!", reply_markup=get_start_keyboard(query.from_user))
    elif action == "workers":
        new_workers = data["new_workers"]
        db.update_project(project_id, new_workers=new_workers)
        await query.message.answer("Сотрудники проекта успешно изменены!",
                                   reply_markup=get_start_keyboard(query.from_user))

    await state.clear()
    await query.answer()


# ===================== Add Task Type Handlers =====================
@admin_router.message(F.text == "Добавить тип задачи")
async def add_task_type_command(message: types.Message, state: FSMContext):
    await state.set_state(AddTaskType.name)
    await message.answer("Введите название типа задачи:", reply_markup=add_cancel_button())


@admin_router.message(StateFilter(AddTaskType.name))
async def add_task_type_name(message: types.Message, state: FSMContext):
    task_name = message.text
    existing_task = db.get_task_by_name(task_name)
    if existing_task:
        await message.answer("Тип задачи с таким названием уже существует.",
                             reply_markup=get_start_keyboard(message.from_user))
        await state.clear()
        return

    await state.update_data(name=task_name)
    await state.set_state(AddTaskType.confirm)
    await message.answer(f"Вы уверены, что хотите добавить тип задачи '{task_name}'?",
                         reply_markup=add_cancel_button(confirm_keyboard()))


@admin_router.callback_query(StateFilter(AddTaskType.confirm), F.data == "confirm")
async def add_task_type_confirm(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_name = data["name"]
    db.create_task(name=task_name)
    await query.message.answer("Тип задачи успешно добавлен!", reply_markup=get_start_keyboard(query.from_user))
    await state.clear()
    await query.answer()


# ===================== Add Worker Handlers =====================
@admin_router.message(F.text == "Добавить сотрудника")
async def add_worker_command(message: types.Message, state: FSMContext):
    await state.set_state(AddWorker.name)
    await message.answer("Введите имя нового сотрудника:", reply_markup=add_cancel_button())


@admin_router.message(StateFilter(AddWorker.name))
async def add_worker_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddWorker.position)
    await message.answer("Введите должность нового сотрудника:", reply_markup=add_cancel_button())


@admin_router.message(StateFilter(AddWorker.position))
async def add_worker_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text)
    await state.set_state(AddWorker.telegram_id)

    await message.answer(
        "Кнопка для возврата",
        reply_markup=add_cancel_button()
    )
    await message.answer(
        "Нажмите кнопку ниже, чтобы выбрать сотрудника.",
        reply_markup=get_worker_keyboard()
    )


@admin_router.message(StateFilter(AddWorker.telegram_id), F.user_shared)
async def add_worker_telegram_id(message: types.Message, state: FSMContext):
    if message.user_shared.request_id == 1:
        telegram_id = message.user_shared.user_id
        if db.get_worker_by_telegram_id(telegram_id) != None:
            await message.answer("Этот сотрудник уже добавлен", reply_markup=get_start_keyboard(message.from_user))
            await state.clear()
            return

        await state.update_data(telegram_id=telegram_id)
        data = await state.get_data()
        name = data["name"]
        position = data["position"]
        await message.answer(
            f"Подтвердите добавление сотрудника:\n"
            f"Имя: {name}\n"
            f"Должность: {position}\n"
            f"Telegram ID: {telegram_id}",
            reply_markup=add_cancel_button(confirm_keyboard()),
        )
        await state.set_state(AddWorker.confirm)
    else:
        await message.answer("Неверный request_id.", reply_markup=get_start_keyboard(message.from_user))
        await state.clear()


@admin_router.callback_query(StateFilter(AddWorker.confirm), F.data == "confirm")
async def add_worker_confirm(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    position = data["position"]
    telegram_id = data["telegram_id"]

    db.create_worker(name=name, position=position, telegram_id=telegram_id)
    await query.message.answer("Сотрудник успешно добавлен!", reply_markup=get_start_keyboard(query.from_user))
    await state.clear()
    await query.answer()
