from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from datetime import time

from data.worker_operations import WorkerOperations
from widgets.Vertical import Select


class ReminderSettingsStates(StatesGroup):
    select_day = State()
    select_time = State()
    confirmation = State()


async def get_days_of_week(dialog_manager: DialogManager, **kwargs):
    days = [
        {"value": "понедельник", "label": "Понедельник"},
        {"value": "вторник", "label": "Вторник"},
        {"value": "среда", "label": "Среда"},
        {"value": "четверг", "label": "Четверг"},
        {"value": "пятница", "label": "Пятница"},
        {"value": "суббота", "label": "Суббота"},
        {"value": "воскресенье", "label": "Воскресенье"},
    ]

    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id

    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)
    current_day = worker.get('reminder_day', 'пятница')

    return {
        "days": days,
        "current_day": current_day
    }


async def on_day_selected(callback: CallbackQuery, widget: Select,
                          dialog_manager: DialogManager, selected_item: str):
    dialog_manager.dialog_data['selected_day'] = selected_item
    await dialog_manager.next()


async def get_time_input(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id

    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)
    current_time = worker.get('reminder_time', time(17, 0)).strftime("%H:%M")

    return {
        "current_time": current_time,
    }


async def on_time_entered(message: Message, widget: TextInput,
                          dialog_manager: DialogManager, time_str: str):
    try:
        # Validate time format
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError

        dialog_manager.dialog_data['selected_time'] = time_str
        await dialog_manager.next()
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, введите время в формате ЧЧ:MM (например, 17:00)")
        return


async def get_confirmation_data(dialog_manager: DialogManager, **kwargs):
    return {
        "day": dialog_manager.dialog_data['selected_day'],
        "time": dialog_manager.dialog_data['selected_time']
    }


async def on_confirmation(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data['db']
    notification_sender = dialog_manager.middleware_data['notification_sender']

    telegram_id = dialog_manager.event.from_user.id
    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)

    selected_day = dialog_manager.dialog_data['selected_day']
    selected_time = dialog_manager.dialog_data['selected_time']

    if selected_day and selected_time:
        WorkerOperations.update_worker_reminder_settings(
            db,
            worker['id'],
            day=selected_day,
            time=selected_time
        )

        await notification_sender.on_data_changed(worker['id'])

        await callback.message.answer(
            f"Напоминания установлены на {selected_day} в {selected_time}!"
        )
    else:
        await callback.message.answer("Не удалось установить напоминания!")

    await dialog_manager.done()


def edit_reminder_settings_dialog():
    return Dialog(
        Window(
            Const("Выберите день недели для напоминаний:"),
            Select(
                Format("{item[label]}"),
                id="s_day",
                item_id_getter=lambda item: item["value"],
                items="days",
                on_click=on_day_selected,
            ),
            Cancel(Const("❌ Отмена")),
            state=ReminderSettingsStates.select_day,
            getter=get_days_of_week,
        ),
        Window(
            Const("Введите время для напоминаний (МСК):\n(например 17:00)"),

            TextInput(
                id="time_input",
                type_factory=str,
                on_success=on_time_entered,
            ),
            Cancel(Const("❌ Отмена")),
            state=ReminderSettingsStates.select_time,
            getter=get_time_input,
        ),
        Window(
            Format("Установить напоминания на {day} в {time}?"),
            Row(
                Cancel(Const("❌ Нет")),
                Button(Const("✅ Да"), id="confirm", on_click=on_confirmation),
            ),
            state=ReminderSettingsStates.confirmation,
            getter=get_confirmation_data,
        )
    )
