from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel, Select
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput



class TimeEntryStates(StatesGroup):
    select_project = State()
    select_task = State()
    enter_hours = State()
    confirm = State()

async def time_entry_start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(TimeEntryStates.select_project)


async def get_projects(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    worker = await db.get_worker_by_telegram_id(dialog_manager.event.from_user.id)

    # Здесь должна быть логика получения доступных проектов для сотрудника
    # Например:
    projects = await db.get_all_projects()  # В реальности нужно фильтровать по доступным проектам

    return {
        "projects": [
            (f"{project['name']} ({project['type']})", project["id"])
            for project in projects
        ]
    }


async def get_tasks(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    worker = await db.get_worker_by_telegram_id(dialog_manager.event.from_user.id)
    project_id = dialog_manager.dialog_data["project_id"]

    # Получаем задачи, доступные для отдела сотрудника
    position = await db.get_position(worker["position_id"])
    department_type = position["department_type"]

    # Получаем задачи проекта, которые соответствуют отделу сотрудника
    tasks = await db.get_project_tasks(project_id)
    filtered_tasks = [
        task for task in tasks
        if task["department_type"] == department_type or task["department_type"] is None
    ]

    return {
        "tasks": [
            (f"{task['name']} ({task['stage']})" if task['stage'] else task['name'], task["id"])
            for task in filtered_tasks
        ]
    }


async def on_project_selected(callback, select, dialog_manager, item_id):
    dialog_manager.dialog_data["project_id"] = item_id
    await dialog_manager.next()


async def on_task_selected(callback, select, dialog_manager, item_id):
    dialog_manager.dialog_data["task_id"] = item_id
    await dialog_manager.next()


async def on_hours_entered(message: Message, widget, dialog_manager: DialogManager, hours: str):
    try:
        hours_float = float(hours.replace(",", "."))
        if hours_float <= 0:
            raise ValueError
        dialog_manager.dialog_data["hours"] = hours_float
        await dialog_manager.next()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число часов (больше 0)")


async def get_confirmation_data(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    project_id = dialog_manager.dialog_data["project_id"]
    task_id = dialog_manager.dialog_data["task_id"]

    project = await db.get_project(project_id)
    task = await db.get_task(task_id)

    return {
        "project_name": project["name"],
        "task_name": task["name"],
        "hours": dialog_manager.dialog_data["hours"]
    }


async def on_confirmation(callback, button, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data["db"]
    worker = await db.get_worker_by_telegram_id(dialog_manager.event.from_user.id)

    await db.add_time_entry(
        project_id=dialog_manager.dialog_data["project_id"],
        worker_id=worker["id"],
        task_id=dialog_manager.dialog_data["task_id"],
        hours=dialog_manager.dialog_data["hours"]
    )

    await callback.answer("Время успешно добавлено!")
    await dialog_manager.done()


time_entry_dialog = Dialog(
    Window(
        Const("Выберите проект:"),
        Select(
            Format("{item[0]}"),
            id="s_projects",
            item_id_getter=lambda item: item[1],
            items="projects",
            on_click=on_project_selected,
        ),
        Cancel(Const("Отмена")),
        state=TimeEntryStates.select_project,
        getter=get_projects,
    ),
    Window(
        Const("Выберите задачу:"),
        Select(
            Format("{item[0]}"),
            id="s_tasks",
            item_id_getter=lambda item: item[1],
            items="tasks",
            on_click=on_task_selected,
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=TimeEntryStates.select_task,
        getter=get_tasks,
    ),
    Window(
        Const("Введите количество часов:"),
        TextInput(
            id="hours_input",
            type_factory=str,
            on_success=on_hours_entered,
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=TimeEntryStates.enter_hours,
    ),
    Window(
        Format(
            "Подтвердите добавление времени:\n\n"
            "Проект: {project_name}\n"
            "Задача: {task_name}\n"
            "Часы: {hours}"
        ),
        Button(
            Const("Подтвердить"),
            id="confirm",
            on_click=on_confirmation,
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=TimeEntryStates.confirm,
        getter=get_confirmation_data,
    ),
)