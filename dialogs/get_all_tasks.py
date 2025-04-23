from typing import Any
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram.types import CallbackQuery

from widgets.Vertical import Select


class AllTasksState(StatesGroup):
    show_tasks = State()
    task_detail = State()


async def get_all_tasks_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    tasks = db.get_all_tasks()
    return {
        "tasks": tasks,
        "count": len(tasks),
    }


async def get_task_detail_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    task_id = dialog_manager.current_context().dialog_data["selected_task_id"]
    task = db.get_task(task_id)

    stage = task["stage"] if task["stage"] else "Не указан"
    dept_type = task["department_type"] if task["department_type"] else "Не указан"

    return {
        "task_id": task["id"],
        "task_name": task["name"],
        "task_stage": stage,
        "task_dept": dept_type,
    }


async def on_task_selected(callback: CallbackQuery, select: Select,
                           dialog_manager: DialogManager, item_id: str):
    dialog_manager.current_context().dialog_data["selected_task_id"] = item_id
    await dialog_manager.next()


async def on_back_to_list(callback: CallbackQuery, button: Button,
                          dialog_manager: DialogManager):
    await dialog_manager.back()


def get_all_tasks_dialog():
    return Dialog(
        Window(
            Format("Всего задач: {count}\n\nВыберите задачу:"),
            Select(
                Format("{item[name]} (ID: {item[id]})"),
                id="tasks_select",
                item_id_getter=lambda x: x["id"],
                items="tasks",
                on_click=on_task_selected,
            ),
            Cancel(Const("❌ Закрыть")),
            state=AllTasksState.show_tasks,
            getter=get_all_tasks_getter,
        ),
        Window(
            Format(
                "<b>Информация о задаче</b>\n\n"
                "ID: {task_id}\n"
                "Название: {task_name}\n"
                "Этап: {task_stage}\n"
                "Отдел: {task_dept}"
            ),
            Back(Const("⬅️ Назад к списку")),
            Cancel(Const("❌ Закрыть")),
            state=AllTasksState.task_detail,
            getter=get_task_detail_getter,
        ),
    )