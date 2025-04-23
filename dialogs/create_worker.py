from typing import Any
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel, RequestContact
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.kbd import Select

from widgets.RequestUser import RequestUser
from widgets.Vertical import Multiselect


class CreateWorkerState(StatesGroup):
    name = State()
    department = State()
    position = State()
    contact = State()
    weekly_hours = State()
    permissions = State()
    confirm = State()


async def worker_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    data = dialog_manager.current_context().dialog_data

    department = data.get("department")
    position_id = data.get("position_id")

    all_positions = db.get_all_positions()

    positions = []
    if department:
        positions = [p for p in all_positions if p['department_type'] == department]
    else:
        positions = all_positions

    position_items = [(p['id'], p['name']) for p in positions]

    position_name = "Не выбрана"
    if position_id:
        position = next((p for p in all_positions if p['id'] == position_id), None)
        if position:
            position_name = position['name']

    permissions = []
    if data.get("can_receive_custom_tasks", False):
        permissions.append("Кастомные задачи")
    if data.get("can_receive_non_project_tasks", False):
        permissions.append("Непроектные задачи")

    return {
        "name": data.get("name", "Не указано"),
        "department": "Не указан" if not department else department,
        "position_items": position_items,
        "position_name": position_name,
        "telegram_id": data.get("telegram_id", "Не указан"),
        "weekly_hours": data.get("weekly_hours", "Не указано"),
        "can_receive_custom_tasks": data.get("can_receive_custom_tasks", False),
        "can_receive_non_project_tasks": data.get("can_receive_non_project_tasks", False),
        "permissions": permissions,
    }


async def on_name_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Имя сотрудника не может быть пустым. Пожалуйста, введите имя.")
        return

    dialog_manager.current_context().dialog_data["name"] = message.text.strip()
    await dialog_manager.next()


async def on_department_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    dialog_manager.current_context().dialog_data["department"] = item_id
    await dialog_manager.next()


async def on_position_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id: str):
    dialog_manager.current_context().dialog_data["position_id"] = int(item_id)
    await dialog_manager.next()


async def on_contact_received(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    print(message.user_shared.user_id)
    dialog_manager.current_context().dialog_data["telegram_id"] = message.user_shared.user_id
    await dialog_manager.next()


async def on_hours_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    try:
        hours = int(message.text.strip())
        if hours <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество часов (целое число больше 0).")
        return

    dialog_manager.current_context().dialog_data["weekly_hours"] = hours
    await dialog_manager.next()


async def on_continue_from_permissions(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    widget = dialog_manager.find("perms_ms")
    selected_items = widget.get_checked()
    data = dialog_manager.current_context().dialog_data
    data.update({
        "can_receive_custom_tasks": ("custom_tasks" in selected_items),
        "can_receive_non_project_tasks": ("non_project_tasks" in selected_items),
    })

    await dialog_manager.next()


async def create_worker(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    db = dialog_manager.middleware_data["db"]

    try:
        worker_id = db.create_worker(
            name=data["name"],
            telegram_id=data["telegram_id"],
            position_id=data["position_id"],
            weekly_hours=data["weekly_hours"],
            can_receive_custom_tasks=data.get("can_receive_custom_tasks", False),
            can_receive_non_project_tasks=data.get("can_receive_non_project_tasks", False)
        )
        await callback.answer(f"Сотрудник успешно добавлен (ID: {worker_id})")
    except Exception as e:
        await callback.answer(f"Ошибка при добавлении сотрудника: {str(e)}")
    await dialog_manager.done()


def create_worker_dialog():
    return Dialog(
        Window(
            Const("Введите имя сотрудника:"),
            MessageInput(
                func=on_name_entered,
                content_types=["text"]
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateWorkerState.name,
            getter=worker_getter,
        ),
        Window(
            Const("Выберите отдел сотрудника:"),
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
            state=CreateWorkerState.department,
            getter=worker_getter,
        ),
        Window(
            Const("Выберите должность сотрудника:"),
            Select(
                text=Format("{item[1]}"),
                items="position_items",
                id="position_select",
                item_id_getter=lambda x: x[0],
                on_click=on_position_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateWorkerState.position,
            getter=worker_getter,
        ),
        Window(
            Const("Отправьте контакт сотрудника или его Telegram ID:"),
            RequestUser(
                Const("Отправить контакт"),
            ),
            MessageInput(
                func=on_contact_received,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateWorkerState.contact,
            getter=worker_getter,
            markup_factory=ReplyKeyboardFactory(resize_keyboard=True, one_time_keyboard=True),
        ),
        Window(
            Const("Введите количество рабочих часов в неделю:"),
            MessageInput(
                func=on_hours_entered,
                content_types=["text"]
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateWorkerState.weekly_hours,
            getter=worker_getter,
        ),
        Window(
            Const("Установите разрешения для сотрудника:"),
            Multiselect(
                checked_text=Format("✅ {item[0]}"),
                unchecked_text=Format("❌ {item[0]}"),
                items=[
                    ("Кастомные задачи", "custom_tasks"),
                    ("Непроектные задачи", "non_project_tasks"),
                ],
                id="perms_ms",
                item_id_getter=lambda x: x[1],
            ),
            Button(
                Const("➡️ Продолжить"),
                id="continue",
                on_click=on_continue_from_permissions,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateWorkerState.permissions,
            getter=worker_getter,
        ),
        Window(
            Format(
                "Подтвердите добавление сотрудника:\n\n"
                "Имя: {name}\n"
                "Отдел: {department}\n"
                "Должность: {position_name}\n"
                "Telegram ID: {telegram_id}\n"
                "Часов в неделю: {weekly_hours}\n"
                "Разрешения: {permissions}\n"
            ),
            Button(
                Const("✅ Добавить сотрудника"),
                id="confirm",
                on_click=create_worker
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateWorkerState.confirm,
            getter=worker_getter,
        ),
    )
