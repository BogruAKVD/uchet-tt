from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Cancel, Button, Select
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram.types import Message
from typing import Any

from data.task_operations import TaskOperations


class CreateNonProjectTaskState(StatesGroup):
    select_department = State()
    enter_task_name = State()
    confirm = State()

async def get_task_data(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.dialog_data
    return {
        "department": data.get("department"),
        "task_name": data.get("task_name"),
    }

async def on_department_selected(callback: Any, widget: Any, dialog_manager: DialogManager, item_id: str):
    dialog_manager.current_context().dialog_data["department"] = None if item_id == "None" else item_id
    await dialog_manager.next()

async def on_task_name_entered(message: Message, widget: Any, dialog_manager: DialogManager, task_name: str):
    dialog_manager.dialog_data["task_name"] = task_name
    await dialog_manager.next()

async def on_confirm(callback: Any, widget: Any, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data['db']
    task_name = dialog_manager.dialog_data["task_name"]
    department = dialog_manager.dialog_data["department"]

    task_id = TaskOperations.add_nonproject_task(db, task_name, department)

    if task_id:
        await callback.message.answer(
            f"Непроектная задача '{task_name}' для отдела {department} успешно добавлена!"
        )
    else:
        await callback.message.answer("Не удалось добавить задачу. Пожалуйста, попробуйте позже.")

    await dialog_manager.done()

def create_nonproject_task_dialog():
    return Dialog(
        Window(
            Const("Выберите отдел для непроектной задачи:"),
            Select(
                text=Format("{item[1]}"),
                id="s_departments",
                item_id_getter=lambda x: x[0],
                items=[
                    ("шрифтовой", "Шрифтовой"),
                    ("технический", "Технический"),
                    ("графический", "Графический"),
                    (None, "Без отдела"),
                ],
                on_click=on_department_selected,
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateNonProjectTaskState.select_department,
        ),
        Window(
            Const("Введите название для новой непроектной задачи:"),
            TextInput(
                id="task_name_input",
                on_success=on_task_name_entered,
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateNonProjectTaskState.enter_task_name,
        ),
        Window(
            Format("Подтвердите создание непроектной задачи:\n\n"
                  "Название: {task_name}\n"
                  "Отдел: {department}"),
            Button(
                Const("✅ Подтвердить"),
                id="confirm",
                on_click=on_confirm,
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateNonProjectTaskState.confirm,
            getter=get_task_data,
        ),
    )