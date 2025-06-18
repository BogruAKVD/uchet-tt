from datetime import datetime
from io import BytesIO

from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Document, BufferedInputFile, CallbackQuery, Message
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram_dialog.widgets.kbd import Row, Cancel, Button
import pandas as pd
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput


class ImportTimeTableStates(StatesGroup):
    upload = State()
    confirm = State()


async def on_file_uploaded(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    document = message.document
    if not document or not document.file_name.endswith(".xlsx"):
        await message.answer("⚠️ Пожалуйста, загрузите .xlsx файл")
        return

    file_id = document.file_id
    file = await dialog_manager.event.bot.get_file(file_id)
    file_path = file.file_path

    file_bytes = BytesIO()
    await dialog_manager.event.bot.download_file(file_path, file_bytes)
    file_bytes.seek(0)

    df = pd.read_excel(file_bytes, sheet_name="Табель")
    df = df[df["Тип"] == "Задача"]

    dialog_manager.dialog_data["xlsx_df"] = df
    await dialog_manager.switch_to(ImportTimeTableStates.confirm)


async def get_diffs(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    telegram_id = dialog_manager.event.from_user.id
    df = dialog_manager.dialog_data.get("xlsx_df")

    with db.conn.cursor() as cursor:
        cursor.execute("SELECT id FROM worker WHERE telegram_id = %s", (telegram_id,))
        row = cursor.fetchone()
        if not row:
            return {"preview": "Пользователь не найден в базе."}
        worker_id = row[0]

        cursor.execute("""
            SELECT project_task_id, entry_date, hours
            FROM time_entry
            WHERE worker_id = %s
        """, (worker_id,))
        db_entries = cursor.fetchall()
        db_map = {(r[0], r[1]): r[2] for r in db_entries}

        file_map = {}
        diffs = []

        for _, row in df.iterrows():
            task_id = int(row["project_task_id"])
            for col in df.columns[5:]:
                if pd.isna(row[col]) or row[col] == '':
                    continue
                entry_date = datetime.strptime(col, "%d.%m.%Y").date()
                hours = float(row[col])
                file_map[(task_id, entry_date)] = hours

                if (task_id, entry_date) not in db_map:
                    diffs.append(("🆕 добавить", task_id, entry_date, None, hours))
                elif round(db_map[(task_id, entry_date)], 2) != round(hours, 2):
                    diffs.append(("✏️ изменить", task_id, entry_date, db_map[(task_id, entry_date)], hours))

        for key, old_hours in db_map.items():
            if key[0] in df["project_task_id"].values and key not in file_map:
                diffs.append(("❌ удалить", key[0], key[1], old_hours, None))

    dialog_manager.dialog_data["diffs"] = diffs

    preview = "\n".join(
        f"{mark} task_id={task_id}, {entry_date}: {old or ''} → {new or ''}"
        for mark, task_id, entry_date, old, new in diffs[:50]
    )
    if len(diffs) > 50:
        preview += "\n...и другие"
    return {"preview": preview or "Нет изменений"}

async def apply_diff(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data["db"]
    telegram_id = dialog_manager.event.from_user.id
    diffs = dialog_manager.dialog_data["diffs"]

    with db.conn.cursor() as cursor:
        cursor.execute("SELECT id FROM worker WHERE telegram_id = %s", (telegram_id,))
        worker_id = cursor.fetchone()[0]

        for action, task_id, entry_date, old, new in diffs:
            if action == "🆕 добавить":
                cursor.execute("""
                    INSERT INTO time_entry (worker_id, project_task_id, entry_date, hours)
                    VALUES (%s, %s, %s, %s)
                """, (worker_id, task_id, entry_date, new))
            elif action == "✏️ изменить":
                cursor.execute("""
                    UPDATE time_entry SET hours = %s
                    WHERE worker_id = %s AND project_task_id = %s AND entry_date = %s
                """, (new, worker_id, task_id, entry_date))
            elif action == "❌ удалить":
                cursor.execute("""
                    DELETE FROM time_entry
                    WHERE worker_id = %s AND project_task_id = %s AND entry_date = %s
                """, (worker_id, task_id, entry_date))

    db.conn.commit()
    await callback.message.answer(f"✅ Изменения применены: {len(diffs)} операций")
    await dialog_manager.done()

def import_time_table_dialog():
    return Dialog(
        Window(
            Const("Загрузите Excel файл с табелем"),
            MessageInput(on_file_uploaded, content_types=["document"]),
            Cancel(Const("❌ Отмена")),
            state=ImportTimeTableStates.upload,
        ),
        Window(
            Format("🔍 Найдены изменения:\n\n{preview}"),
            Button(Const("✅ Применить изменения"), id="apply", on_click=apply_diff),
            Cancel(Const("❌ Отмена")),
            getter=get_diffs,
            state=ImportTimeTableStates.confirm,
        )
    )


