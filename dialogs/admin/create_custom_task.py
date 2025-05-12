from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Cancel, Button
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram.types import Message
from typing import Any

from widgets.Vertical import Select


class CreateCustomTaskState(StatesGroup):
    select_font = State()
    enter_task_name = State()
    confirm = State()


async def get_fonts(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    return {
        "fonts": db.get_fonts(),
    }



async def get_task_data(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.dialog_data
    return {
        "font_name": data.get("font_name"),
        "task_name": data.get("task_name"),
    }


async def on_font_selected(callback: Any, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["font_id"] = int(item_id)
    with manager.middleware_data['db'].conn.cursor() as cursor:
        cursor.execute("SELECT name FROM font WHERE id = %s", (item_id,))
        font_name = cursor.fetchone()[0]
    manager.dialog_data["font_name"] = font_name
    await manager.next()


async def on_task_name_entered(message: Message, widget: Any, manager: DialogManager, task_name: str):
    manager.dialog_data["task_name"] = task_name
    await manager.next()


async def on_confirm(callback: Any, widget: Any, manager: DialogManager):
    db = manager.middleware_data['db']
    task_name = manager.dialog_data["task_name"]
    font_id = manager.dialog_data["font_id"]

    task_id = db.add_custom_task(task_name, font_id)

    if task_id:
        await callback.message.answer(f"Кастомная задача '{task_name}' успешно добавлена!")
    else:
        await callback.message.answer("Не удалось добавить задачу. Пожалуйста, попробуйте позже.")

    await manager.done()



def create_custom_task_dialog():
    return Dialog(
        Window(
            Const("Выберите шрифт для новой кастомной задачи:"),
            Select(
                Format("{item[1]}"),
                id="s_fonts",
                item_id_getter=lambda x: x[0],
                items="fonts",
                on_click=on_font_selected,
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateCustomTaskState.select_font,
            getter=get_fonts,
        ),
        Window(
            Const("Введите название для новой кастомной задачи:"),
            TextInput(
                id="task_name_input",
                on_success=on_task_name_entered,
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateCustomTaskState.enter_task_name,
        ),
        Window(
            Format("Подтвердите создание кастомной задачи:\n\n"
                   "Название: {task_name}\n"
                   "Шрифт: {font_name}"),
            Button(
                Const("✅ Подтвердить"),
                id="confirm",
                on_click=on_confirm,
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateCustomTaskState.confirm,
            getter=get_task_data,
        ),
    )