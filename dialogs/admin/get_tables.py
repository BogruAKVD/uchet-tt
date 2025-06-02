from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const
from aiogram.types import CallbackQuery, BufferedInputFile


from data.export_tables import TableExporter
from data.database import Database

class GetTablesState(StatesGroup):
    main = State()


async def export_tables(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    db = Database()
    zip_buffer = TableExporter.export_all_tables_to_zip(db)

    zip_file = BufferedInputFile(zip_buffer.getvalue(), filename="tables_export.zip")

    await callback.message.answer_document(
        document=zip_file,
        caption="Экспорт всех таблиц в формате CSV"
    )

    await dialog_manager.done()


def get_tables_dialog() :
    return Dialog(
        Window(
            Const("Нажмите кнопку чтобы получить архив со всеми таблицами в CSV формате"),
            Button(
                text=Const("Экспортировать таблицы"),
                id="export",
                on_click=export_tables,
            ),
            state=GetTablesState.main,
        ),
    )
