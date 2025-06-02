from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row
from aiogram_dialog.widgets.text import Const, Format

from data.project_operations import ProjectOperations
from data.worker_operations import WorkerOperations
from widgets.Vertical import Multiselect


class ProjectSelectStates(StatesGroup):
    select_projects = State()


async def get_projects(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id
    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)

    available_projects = ProjectOperations.get_available_projects(db, worker['id'])
    active_projects = WorkerOperations.get_worker_active_projects(db, worker['id'])

    return {
        "available_projects": available_projects,
        "active_projects": active_projects
    }


async def on_dialog_start(start_data: dict, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id
    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)


    active_project_ids = WorkerOperations.get_worker_active_projects(db, worker['id'])
    widget = dialog_manager.find("m_projects")
    for active_project_id in active_project_ids:
        await widget.set_checked(active_project_id, True)


async def on_project_selected(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.next()


async def on_confirmation(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id
    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)
    selected_projects = dialog_manager.find("m_projects").get_checked()

    WorkerOperations.set_worker_active_projects(db, worker['id'], selected_projects)
    await callback.message.answer("Проекты успешно добавлены!")

    await dialog_manager.done()


def select_projects_dialog():
    return Dialog(
        Window(
            Const("Выберите проекты для добавления:"),
            Multiselect(
                checked_text=Format("✅ {item[name]}"),
                unchecked_text=Format("❌ {item[name]}"),
                id="m_projects",
                item_id_getter=lambda item: item["id"],
                items="available_projects"

            ),
            Row(
                Cancel(Const("❌ Отмена")),
                Button(Const("✅ Подтвердить"), id="next", on_click=on_confirmation),
            ),
            state=ProjectSelectStates.select_projects,
            getter=get_projects,

        ),
        on_start=on_dialog_start,
    )
