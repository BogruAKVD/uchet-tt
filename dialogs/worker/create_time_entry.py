from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Back
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput

from widgets.Vertical import Select


class TimeEntryStates(StatesGroup):
    select_project = State()
    select_task = State()
    enter_hours = State()
    confirmation = State()


async def get_active_projects(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id
    worker = db.get_worker_by_telegram_id(telegram_id)

    active_projects = db.get_worker_active_projects_full(worker['id'])

    if worker.get('can_receive_custom_tasks', False):
        custom_project = db.get_custom_project()
        active_projects.insert(0, custom_project)


    return {
        "active_projects": active_projects,
    }


async def get_project_tasks(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    project_id = dialog_manager.dialog_data.get("project_id")

    project_tasks = db.get_tasks_for_project(project_id)

    return {
        "project_tasks": project_tasks,
        "project_name": db.get_project_name(project_id)
    }


async def project_selected(callback: CallbackQuery, widget: Select,
                           manager: DialogManager, item_id: str):
    manager.dialog_data["project_id"] = int(item_id)
    await manager.next()


async def task_selected(callback: CallbackQuery, widget: Select,
                        manager: DialogManager, item_id: str):
    manager.dialog_data["project_task_id"] = int(item_id)
    await manager.next()


async def hours_entered(message: Message, widget: TextInput,
                        manager: DialogManager, hours: str):
    try:
        hours_float = float(hours)
        if hours_float <= 0:
            raise ValueError
        manager.dialog_data["hours"] = hours_float
        await manager.next()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число часов (больше 0)")


async def get_confirmation_data(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    project_task_id = dialog_manager.dialog_data.get("project_task_id")
    hours = dialog_manager.dialog_data.get("hours")

    project_task_info = db.get_project_task_info(project_task_id)

    return {
        "project_name": project_task_info['project_name'],
        "task_name": project_task_info['task_name'],
        "font_name": project_task_info.get('font_name', 'Не указан'),
        "project_task_id": project_task_id,
        "hours": hours
    }


async def save_time_entry(callback: CallbackQuery, button: Button,
                          manager: DialogManager):
    db = manager.middleware_data['db']
    notification_sender = manager.middleware_data['notification_sender']
    telegram_id = manager.event.from_user.id
    worker = db.get_worker_by_telegram_id(telegram_id)

    time_entry_data = {
        "project_task_id": manager.dialog_data["project_task_id"],
        "worker_id": worker['id'],
        "hours": manager.dialog_data["hours"]
    }

    try:
        db.add_time_entry(time_entry_data)
        await notification_sender.on_data_changed(worker['id'])

        await callback.message.answer("Время успешно сохранено!")
    except Exception as e:
        await callback.message.answer(f"Ошибка при сохранении: {str(e)}")

    await manager.done()


def create_time_entry_dialog():
    return Dialog(
        Window(
            Const("Выберите проект:"),
            Select(
                text=Format("{item[name]}"),
                id="s_projects",
                item_id_getter=lambda item: item["id"],
                items="active_projects",
                on_click=project_selected
            ),
            Cancel(Const("❌ Отмена")),
            state=TimeEntryStates.select_project,
            getter=get_active_projects
        ),
        Window(
            Format("Выберите задачу для проекта {project_name}:"),
            Select(
                text=Format("{item[name]} | {item[font_name]}"),
                id="s_tasks",
                item_id_getter=lambda item: item["id"],
                items="project_tasks",
                on_click=task_selected
            ),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Отмена")),
            state=TimeEntryStates.select_task,
            getter=get_project_tasks
        ),
        Window(
            Const("Введите количество потраченных часов (например, 1.5):"),
            TextInput(
                id="hours_input",
                type_factory=float,
                on_success=hours_entered
            ),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Отмена")),
            state=TimeEntryStates.enter_hours
        ),
        Window(
            Format("Подтвердите ввод времени:\n\n"
                   "Проект: {project_name}\n"
                   "Задача: {task_name}\n"
                   "Шрифт: {font_name}\n"
                   "Часы: {hours}"),
            Button(Const("✅ Подтвердить"), id="confirm", on_click=save_time_entry),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Отмена")),
            state=TimeEntryStates.confirmation,
            getter=get_confirmation_data
        )
    )