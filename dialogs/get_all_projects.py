from typing import Any, List, Dict
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel, Select, Column
from aiogram_dialog.widgets.text import Const, Format
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.input import MessageInput

from database import Status
from widgets.Vertical import Select as VerticalSelect, Multiselect


class ProjectState(StatesGroup):
    list_projects = State()
    edit_project = State()
    change_status = State()
    manage_workers = State()


async def projects_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    projects = db.get_all_projects()
    return {
        "projects": [dict(project) for project in projects]
    }


async def project_edit_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    project_id = dialog_manager.current_context().dialog_data["project_id"]

    project = dict(db.get_project(project_id))
    workers = db.get_all_workers()
    project_workers = db.get_project_workers(project_id)

    project_worker_ids = [worker['id'] for worker in project_workers]

    return {
        "project": project,
        "workers": workers,
        "project_worker_ids": project_worker_ids,
        "statuses": [status.value for status in Status],
    }


async def on_project_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    dialog_manager.current_context().dialog_data["project_id"] = item_id
    await dialog_manager.switch_to(ProjectState.edit_project)


async def on_status_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    project_id = dialog_manager.current_context().dialog_data["project_id"]
    db = dialog_manager.middleware_data["db"]

    try:
        db.update_project(project_id, new_status=item_id)
        await callback.answer(f"Статус проекта обновлён")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

    await dialog_manager.switch_to(ProjectState.edit_project)


async def save_workers(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    project_id = dialog_manager.current_context().dialog_data["project_id"]
    db = dialog_manager.middleware_data["db"]

    widget = dialog_manager.find("workers_ms")
    selected_worker_ids = [int(worker_id) for worker_id in widget.get_checked()]

    try:
        db.update_project(project_id, new_workers=selected_worker_ids)
        await callback.answer("Список сотрудников обновлён")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

    await dialog_manager.switch_to(ProjectState.edit_project)


def get_all_projects_dialog():
    return Dialog(
        Window(
            Format("Список проектов:"),
            VerticalSelect(
                Format("{item[name]} ({item[type]}, {item[status]})"),
                id="projects_select",
                item_id_getter=lambda item: item["id"],
                items="projects",
                on_click=on_project_selected,
            ),
            Cancel(Const("❌ Закрыть")),
            state=ProjectState.list_projects,
            getter=projects_getter,
        ),
        Window(
            Format(
                "Проект: {project[name]}\n"
                "Тип: {project[type]}\n"
                "Статус: {project[status]}\n\n"
                "Выберите действие:"
            ),
            Column(
                Button(
                    Const("Изменить статус"),
                    id="change_status",
                    on_click=lambda c, w, d: d.switch_to(ProjectState.change_status)
                ),
                Button(
                    Const("Управление сотрудниками"),
                    id="manage_workers",
                    on_click=lambda c, w, d: d.switch_to(ProjectState.manage_workers)
                ),
            ),
            Back(Const("⬅️ Назад к списку")),
            state=ProjectState.edit_project,
            getter=project_edit_getter,
        ),
        Window(
            Format("Выберите новый статус для проекта {project[name]}:"),
            VerticalSelect(
                Format("{item}"),
                id="status_select",
                item_id_getter=lambda item: item,
                items="statuses",
                on_click=on_status_selected,
            ),
            Back(Const("⬅️ Назад")),
            state=ProjectState.change_status,
            getter=project_edit_getter,
        ),
        Window(
            Format("Выберите сотрудников для проекта {project[name]}:"),
            Multiselect(
                checked_text=Format("✅ {item[name]}"),
                unchecked_text=Format("❌ {item[name]}"),
                items="workers",
                item_id_getter=lambda item: str(item["id"]),
                id="workers_ms",
            ),
            Button(
                Const("💾 Сохранить"),
                id="save_workers",
                on_click=save_workers
            ),
            Back(
                Const("⬅️ Назад"),
                on_click=lambda c, w, d: d.switch_to(ProjectState.edit_project)
            ),
            state=ProjectState.manage_workers,
            getter=project_edit_getter,
        )
    )