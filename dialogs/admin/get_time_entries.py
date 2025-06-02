from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const
from aiogram.types import CallbackQuery, BufferedInputFile
import pandas as pd
import io
import zipfile


class TimeEntryExportState(StatesGroup):
    main = State()


async def export_time_entries(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    db = dialog_manager.middleware_data["db"]

    try:
        with db.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM time_entry_detail")
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()

            df = pd.DataFrame(data, columns=columns)

            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                zip_file.writestr('time_entries_detail.csv', csv_buffer.getvalue())

            zip_buffer.seek(0)
            zip_file = BufferedInputFile(zip_buffer.getvalue(), filename="time_entries_export.zip")

            await callback.message.answer_document(
                document=zip_file,
                caption="Экспорт данных о временных записях с детализацией"
            )

    except Exception as e:
        await callback.message.answer(f"Ошибка при экспорте данных: {str(e)}")

    await dialog_manager.done()


def get_time_entries_dialog():
    return Dialog(
        Window(
            Const("Нажмите кнопку чтобы получить детализированные данные о временных записях в CSV формате"),
            Button(
                text=Const("Экспортировать данные о временных записях"),
                id="export_time_entries",
                on_click=export_time_entries,
            ),
            state=TimeEntryExportState.main,
        ),
    )