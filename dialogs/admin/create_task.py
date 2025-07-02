from typing import Any
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery

from data.task_operations import TaskOperations
from widgets.Vertical import Select


class CreateTaskState(StatesGroup):
    name = State()
    stage = State()
    department = State()
    confirm = State()


async def task_getter(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.current_context().dialog_data

    stage = data.get("stage")
    department = data.get("department")

    return {
        "name": data.get("name", "Не указано"),
        "stage": "Не указан" if stage is None else stage,
        "department": "Не указан" if department is None else department,
        "raw_stage": stage,
        "raw_department": department,
    }


async def on_name_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Название задачи не может быть пустым. Пожалуйста, введите название.")
        return

    dialog_manager.current_context().dialog_data["name"] = message.text.strip()
    await dialog_manager.next()


async def on_stage_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    dialog_manager.current_context().dialog_data["stage"] = None if item_id == "None" else item_id
    await dialog_manager.next()


async def on_department_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    dialog_manager.current_context().dialog_data["department"] = None if item_id == "None" else item_id
    await dialog_manager.next()


async def create_task(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    name = data.get("name")

    stage = data.get("stage")
    department = data.get("department")

    db = dialog_manager.middleware_data["db"]
    try:
        TaskOperations.create_task(db, name=name, stage=stage, department=department)
        await callback.answer("Задача успешно создана")
    except Exception as e:
        await callback.answer(f"Ошибка при создании задачи: {str(e)}")
    await dialog_manager.done()


def create_task_dialog():
    return Dialog(
        Window(
            Const("Введите название новой задачи:"),
            MessageInput(
                func=on_name_entered,
                content_types=["text"]
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateTaskState.name,
            getter=task_getter,
        ),
        Window(
            Const("Выберите этап работы:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("подготовка", "Подготовка"),
                    ("отрисовка прямые", "Отрисовка прямые"),
                    ("отрисовка италики", "Отрисовка италики"),
                    ("отрисовка капитель", "Отрисовка капитель"),
                    ("техничка", "Техничка"),
                    ("оформление", "Оформление"),
                    (None, "Без стадии"),
                ],
                id="stage_select",
                item_id_getter=lambda x: x[0],
                on_click=on_stage_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateTaskState.stage,
            getter=task_getter,
        ),
        Window(
            Const("Выберите тип отдела:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("шрифтовой", "Шрифтовой"),
                    ("технический", "Технический"),
                    ("графический", "Графический"),
                    ("контентный", "Контентный"),
                    (None, "Без отдела"),
                ],
                id="dept_select",
                item_id_getter=lambda x: x[0],
                on_click=on_department_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateTaskState.department,
            getter=task_getter,
        ),
        Window(
            Format(
                "Подтвердите создание задачи:\n\n"
                "Название: {name}\n"
                "Этап: {stage}\n"
                "Отдел: {department}"
            ),
            Button(
                Const("✅ Создать задачу"),
                id="confirm",
                on_click=create_task
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateTaskState.confirm,
            getter=task_getter,
        ),
    )