from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, Back
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from datetime import datetime, timedelta, date

from data.font_operations import FontOperations
from data.project_operations import ProjectOperations
from data.task_operations import TaskOperations
from data.time_entry_operations import TimeEntryOperations
from data.worker_operations import WorkerOperations
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
    worker = WorkerOperations.get_worker_by_telegram_id(db, telegram_id)
    period = dialog_manager.dialog_data.get("period")

    today = datetime.today()

    if period == "today":
        start_date = today - timedelta(days=1)
        entries = TimeEntryOperations.get_time_entries(db, worker['id'], start_date=start_date)
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        entries = TimeEntryOperations.get_time_entries(db, worker['id'], start_date=start_date)
    elif period == "month":
        start_date = datetime(today.year, today.month, 1)
        entries = TimeEntryOperations.get_time_entries(db, worker['id'], start_date=start_date)
    else:
        entries = TimeEntryOperations.get_time_entries(db, worker['id'])

    formatted_entries = []
    for entry in entries:
        project_name = ProjectOperations.get_project_name(db, entry['project_id'])
        task_name = TaskOperations.get_task_name(db, entry['task_id'])
        font_name = FontOperations.get_font_name(db, entry['font_id'])

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

    entry = TimeEntryOperations.get_time_entry(db, entry_id)
    project_name = ProjectOperations.get_project_name(db, entry['project_id'])
    task_name = TaskOperations.get_task_name(db, entry['task_id'])
    font_name = FontOperations.get_font_name(db, entry['font_id'])

    entry_date = entry['entry_date']
    if isinstance(entry_date, str):
        entry_date = datetime.strptime(entry_date, '%Y-%m-%d').date()

    date_str = entry_date.strftime("%d.%m.%Y")

    return {
        "entry_text": f"{date_str}\nПроект: {project_name}\nЗадача: {task_name}\nШрифт: {font_name}\nЧасы: {entry['hours']}",
        "entry_id": entry_id
    }


async def period_selected(callback: CallbackQuery, widget: Select,
                          dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data["period"] = item_id
    await dialog_manager.next()


async def entry_selected(callback: CallbackQuery, widget: Select,
                         dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data["entry_id"] = int(item_id)
    await dialog_manager.next()


async def delete_entry(callback: CallbackQuery, button: Button,
                       dialog_manager: DialogManager):
    db = dialog_manager.middleware_data['db']
    entry_id = dialog_manager.dialog_data["entry_id"]

    TimeEntryOperations.delete_time_entry(db, entry_id)
    await dialog_manager.back()


async def edit_hours_handler(message: Message, widget: TextInput,
                             dialog_manager: DialogManager, hours: float):
    try:
        if hours <= 0:
            raise ValueError

        db = dialog_manager.middleware_data['db']
        entry_id = dialog_manager.dialog_data["entry_id"]
        TimeEntryOperations.update_time_entry(db, entry_id, hours)

        await message.answer("Время успешно обновлено!")
        await dialog_manager.switch_to(ViewTimeEntriesStates.entry_actions)
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
