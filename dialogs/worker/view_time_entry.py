from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, Back
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from datetime import datetime, timedelta, date

from widgets.Vertical import Select


class ViewTimeEntriesStates(StatesGroup):
    select_period = State()
    select_entry = State()
    entry_actions = State()
    edit_hours = State()


async def get_time_periods(dialog_manager: DialogManager, **kwargs):
    return {
        "periods": [
            {"id": "today", "name": "Сегодня"},
            {"id": "week", "name": "Эта неделя"},
            {"id": "month", "name": "Этот месяц"},
            {"id": "all", "name": "Все время"},
        ]
    }


async def get_time_entries(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    telegram_id = dialog_manager.event.from_user.id
    worker = db.get_worker_by_telegram_id(telegram_id)
    period = dialog_manager.dialog_data.get("period", "week")

    today = date.today()

    if period == "today":
        start_date = today
        entries = db.get_time_entries(worker['id'], start_date=start_date)
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        entries = db.get_time_entries(worker['id'], start_date=start_date)
    elif period == "month":
        start_date = date(today.year, today.month, 1)
        entries = db.get_time_entries(worker['id'], start_date=start_date)
    else:
        entries = db.get_time_entries(worker['id'])

    formatted_entries = []
    for entry in entries:
        project_name = db.get_project_name(entry['project_id'])
        task_name = db.get_task_name(entry['task_id'])
        font_name = db.get_font_name(entry['font_id'])  # Assuming you have this method

        entry_date = entry['entry_date']
        if isinstance(entry_date, str):
            entry_date = datetime.strptime(entry_date, '%Y-%m-%d').date()

        date_str = entry_date.strftime("%d.%m.%Y")
        formatted_entries.append({
            "id": entry['id'],
            "text": f"{date_str} | {project_name} - {task_name} ({font_name}): {entry['hours']}ч",
            "hours": entry['hours']
        })

    return {
        "entries": formatted_entries,
        "period": period
    }


async def get_entry_details(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data['db']
    entry_id = dialog_manager.dialog_data["entry_id"]

    entry = db.get_time_entry(entry_id)
    project_name = db.get_project_name(entry['project_id'])
    task_name = db.get_task_name(entry['task_id'])
    font_name = db.get_font_name(entry['font_id'])

    entry_date = entry['entry_date']
    if isinstance(entry_date, str):
        entry_date = datetime.strptime(entry_date, '%Y-%m-%d').date()

    date_str = entry_date.strftime("%d.%m.%Y")

    return {
        "entry_text": f"{date_str}\nПроект: {project_name}\nЗадача: {task_name}\nШрифт: {font_name}\nЧасы: {entry['hours']}",
        "entry_id": entry_id
    }


async def period_selected(callback: CallbackQuery, widget: Select,
                          manager: DialogManager, item_id: str):
    manager.dialog_data["period"] = item_id
    await manager.next()


async def entry_selected(callback: CallbackQuery, widget: Select,
                         manager: DialogManager, item_id: str):
    manager.dialog_data["entry_id"] = int(item_id)
    await manager.next()


async def delete_entry(callback: CallbackQuery, button: Button,
                       manager: DialogManager):
    db = manager.middleware_data['db']
    entry_id = manager.dialog_data["entry_id"]

    db.delete_time_entry(entry_id)
    await manager.back()


async def edit_hours_handler(message: Message, widget: TextInput,
                             manager: DialogManager, hours: float):
    try:
        if hours <= 0:
            raise ValueError

        db = manager.middleware_data['db']
        entry_id = manager.dialog_data["entry_id"]
        db.update_time_entry(entry_id, hours)

        await message.answer("Время успешно обновлено!")
        await manager.switch_to(ViewTimeEntriesStates.entry_actions)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число часов (больше 0)")


def view_time_entries_dialog():
    return Dialog(
        Window(
            Const("Выберите период для просмотра записей:"),
            Select(
                text=Format("{item[name]}"),
                id="s_periods",
                item_id_getter=lambda item: item["id"],
                items="periods",
                on_click=period_selected
            ),
            Cancel(Const("❌ Закрыть")),
            state=ViewTimeEntriesStates.select_period,
            getter=get_time_periods
        ),
        Window(
            Format("Ваши записи за {period}:"),
            Select(
                text=Format("{item[text]}"),
                id="s_entries",
                item_id_getter=lambda item: item["id"],
                items="entries",
                on_click=entry_selected
            ),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Закрыть")),
            state=ViewTimeEntriesStates.select_entry,
            getter=get_time_entries
        ),
        Window(
            Format("Запись:\n\n{entry_text}\n\nВыберите действие:"),
            Button(Const("✏️ Изменить время"), id="edit",
                   on_click=lambda c, b, m: m.switch_to(ViewTimeEntriesStates.edit_hours)),
            Button(Const("🗑️ Удалить"), id="delete", on_click=delete_entry),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Закрыть")),
            state=ViewTimeEntriesStates.entry_actions,
            getter=get_entry_details
        ),
        Window(
            Const("Введите новое количество часов:"),
            TextInput(
                id="hours_edit_input",
                type_factory=float,
                on_success=edit_hours_handler
            ),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Отмена")),
            state=ViewTimeEntriesStates.edit_hours,
            getter=get_entry_details
        )
    )
