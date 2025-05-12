from typing import Any
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.kbd import Select

class CreatePositionState(StatesGroup):
    name = State()
    department_type = State()
    confirm = State()


async def position_getter(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.current_context().dialog_data

    return {
        "name": data.get("name", "Не указано"),
        "department_type": data.get("department_type", "Не указан"),
    }


async def on_name_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Название должности не может быть пустым. Пожалуйста, введите название.")
        return

    dialog_manager.current_context().dialog_data["name"] = message.text.strip()
    await dialog_manager.next()


async def on_department_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    dialog_manager.current_context().dialog_data["department_type"] = item_id
    await dialog_manager.next()


async def create_position(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    name = data.get("name")
    department_type = data.get("department_type")

    db = dialog_manager.middleware_data["db"]
    try:
        position_id = db.create_position(name=name, department_type=department_type)
        await callback.answer(f"Должность '{name}' успешно создана (ID: {position_id})")
    except Exception as e:
        await callback.answer(f"Ошибка при создании должности: {str(e)}")
    finally:
        await dialog_manager.done()


def create_position_dialog():
    return Dialog(
        Window(
            Const("Введите название должности:"),
            MessageInput(
                func=on_name_entered,
                content_types=["text"]
            ),
            Cancel(Const("❌ Отмена")),
            state=CreatePositionState.name,
            getter=position_getter,
        ),
        Window(
            Const("Выберите тип отдела:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("шрифтовой", "Шрифтовой"),
                    ("технический", "Технический"),
                    ("графический", "Графический"),
                ],
                id="dept_select",
                item_id_getter=lambda x: x[0],
                on_click=on_department_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreatePositionState.department_type,
            getter=position_getter,
        ),
        Window(
            Format(
                "Подтвердите создание должности:\n\n"
                "Название: {name}\n"
                "Тип отдела: {department_type}"
            ),
            Button(
                Const("✅ Создать должность"),
                id="confirm",
                on_click=create_position
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreatePositionState.confirm,
            getter=position_getter,
        ),
    )