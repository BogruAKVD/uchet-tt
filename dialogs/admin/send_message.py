from typing import Any
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery

from widgets.Vertical import Multiselect


class SendMessageState(StatesGroup):
    select_workers = State()
    enter_message = State()
    confirm = State()


async def workers_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    workers = db.get_all_workers()

    return {
        "workers": workers,
        "selected": dialog_manager.current_context().dialog_data.get("selected_workers", []),
    }


async def message_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    data = dialog_manager.current_context().dialog_data
    selected_workers = data.get("selected_workers", [])
    workers = db.get_all_workers()
    message_text = data.get("message_text", "Не указано")

    selected_workers_names = [
        worker["name"]
        for worker in workers
        if str(worker["telegram_id"]) in selected_workers
    ]

    return {
        "selected_workers_names": selected_workers_names,
        "message_text": message_text,
    }


async def on_workers_selected(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.current_context().dialog_data["selected_workers"] = dialog_manager.find("workers_ms").get_checked()
    await dialog_manager.next()


async def on_message_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Сообщение не может быть пустым. Пожалуйста, введите текст сообщения.")
        return

    dialog_manager.current_context().dialog_data["message_text"] = message.text.strip()
    await dialog_manager.next()


async def confirm_send(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    selected_workers = data.get("selected_workers", [])
    message_text = data.get("message_text", "")

    message_sender = dialog_manager.middleware_data.get("message_sender")

    if not message_sender:
        await callback.answer("Ошибка: сервис отправки сообщений не доступен")
        return

    success_count = 0
    for worker_id in selected_workers:
        if await message_sender.send_message(user_id=int(worker_id), message=message_text):
            success_count += 1

    await callback.answer(f"Сообщение отправлено {success_count}/{len(selected_workers)} работникам")
    await dialog_manager.done()


def send_message_dialog():
    return Dialog(
        Window(
            Const("Выберите работников для отправки сообщения:"),
            Multiselect(
                checked_text=Format("✅ {item[name]}"),
                unchecked_text=Format("❌ {item[name]}"),
                items="workers",
                id="workers_ms",
                item_id_getter=lambda item: item["telegram_id"],
            ),
            Row(
                Cancel(Const("❌ Отмена")),
                Button(
                    Const("Далее ➡️"),
                    id="next",
                    on_click=on_workers_selected,
                ),
            ),
            state=SendMessageState.select_workers,
            getter=workers_getter,
        ),
        Window(
            Const("Введите текст сообщения:"),
            MessageInput(
                func=on_message_entered,
                content_types=["text"]
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=SendMessageState.enter_message,
        ),
        Window(
            Format(
                "Подтвердите отправку сообщения:\n\n"
                "Получатели: {selected_workers_names}\n"
                "Текст сообщения:\n{message_text}"
            ),
            Button(
                Const("✅ Отправить сообщение"),
                id="confirm_send",
                on_click=confirm_send
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=SendMessageState.confirm,
            getter=message_getter,
        ),
    )