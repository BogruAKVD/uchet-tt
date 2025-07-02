from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput, MessageInput
import pandas as pd
from io import BytesIO
import psycopg2
from datetime import datetime, date, timedelta
import calendar
import re


class ExportTimeTableStates(StatesGroup):
    select_period = State()
    input_custom_range = State()
    processing = State()


async def get_worker_time_data(worker_telegram_id: int, db_conn, start_date: date, end_date: date) -> pd.DataFrame:
    all_dates = []
    current_date = start_date
    while current_date <= end_date:
        all_dates.append(current_date)
        current_date += timedelta(days=1)

    date_columns = [d.strftime('%d.%m.%Y') for d in all_dates]

    with db_conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT p.id, p.name
            FROM worker_active_project wap
            JOIN project p ON wap.project_id = p.id
            JOIN worker w ON wap.worker_id = w.id
            WHERE w.telegram_id = %s
            ORDER BY p.name
        """, (worker_telegram_id,))
        all_projects = cursor.fetchall()

        cursor.execute("""
            SELECT DISTINCT 
                p.id AS project_id,
                p.name AS project_name
            FROM time_entry te
            JOIN worker w ON te.worker_id = w.id
            JOIN project_task pt ON te.project_task_id = pt.id
            JOIN project p ON pt.project_id = p.id
            WHERE w.telegram_id = %s
            AND te.entry_date BETWEEN %s AND %s
        """, (worker_telegram_id, start_date, end_date))
        projects_with_entries = cursor.fetchall()

        unique_projects = {p[0]: p[1] for p in all_projects}
        for p in projects_with_entries:
            unique_projects.setdefault(p[0], p[1])

        result_rows = []

        for project_id, project_name in unique_projects.items():
            result_rows.append({
                'Тип': 'Проект',
                'project_task_id': '',
                'Проект': project_name,
                'Шрифт': '',
                'Задача': '',
                **{d.strftime('%d.%m.%Y'): '' for d in all_dates}
            })

            cursor.execute("""
                SELECT 
                    pt.id, t.name, f.name, te.entry_date, te.hours
                FROM project_task pt
                JOIN task t ON pt.task_id = t.id
                LEFT JOIN font f ON pt.font_id = f.id
                LEFT JOIN time_entry te ON te.project_task_id = pt.id 
                    AND te.worker_id = (SELECT id FROM worker WHERE telegram_id = %s)
                    AND te.entry_date BETWEEN %s AND %s
                WHERE pt.project_id = %s
                ORDER BY t.name, te.entry_date
            """, (worker_telegram_id, start_date, end_date, project_id))

            tasks_data = cursor.fetchall()

            tasks_by_id = {}
            for pt_id, task_name, font_name, entry_date, hours in tasks_data:
                tasks_by_id.setdefault(pt_id, {
                    'task_name': task_name,
                    'font_name': font_name or '',
                    'entries': {}
                })
                if entry_date:
                    date_str = entry_date.strftime('%d.%m.%Y')
                    tasks_by_id[pt_id]['entries'][date_str] = hours

            for pt_id, data in tasks_by_id.items():
                result_rows.append({
                    'Тип': 'Задача',
                    'project_task_id': pt_id,
                    'Проект': project_name,
                    'Шрифт': data['font_name'],
                    'Задача': data['task_name'],
                    **{d.strftime('%d.%m.%Y'): data['entries'].get(d.strftime('%d.%m.%Y'), '') for d in all_dates}
                })

    column_order = ['Тип', 'project_task_id', 'Проект', 'Шрифт', 'Задача'] + date_columns
    df = pd.DataFrame(result_rows)
    for col in column_order:
        if col not in df.columns:
            df[col] = ''

    return df[column_order]


async def export_to_excel(df: pd.DataFrame, filename: str) -> BytesIO:
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Табель')
        workbook = writer.book
        worksheet = writer.sheets['Табель']

        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#D7E4BC', 'border': 1, 'align': 'center',
            'rotation': 90
        })
        project_format = workbook.add_format({'bold': True, 'fg_color': '#B7DEE8', 'border': 1})
        task_format = workbook.add_format({'border': 1})
        hour_format = workbook.add_format({'num_format': '0.00', 'border': 1, 'align': 'center'})

        for col_num, col in enumerate(df.columns):
            worksheet.write(0, col_num, col, header_format)
            worksheet.set_column(col_num, col_num,
                                 12 if col == 'project_task_id' else 18 if col in ['Проект', 'Шрифт', 'Задача'] else 8)

        for row_idx in range(len(df)):
            row = df.iloc[row_idx]
            row_type = row['Тип']

            if row_type == 'Проект':
                fmt = project_format
            else:
                fmt = task_format

            for col_idx, value in enumerate(row):
                if row_type == 'Задача' and df.columns[col_idx] not in ['Тип', 'project_task_id', 'Проект', 'Шрифт',
                                                                        'Задача'] and value != '':
                    worksheet.write(row_idx + 1, col_idx, float(value), hour_format)
                else:
                    worksheet.write(row_idx + 1, col_idx, value, fmt)

    output.seek(0)
    return output


async def process_export_with_dates(message: Message, dialog_manager: DialogManager,
                                    start_date: date, end_date: date):
    try:
        db = dialog_manager.middleware_data['db']
        telegram_id = dialog_manager.event.from_user.id

        df = await get_worker_time_data(telegram_id, db.conn, start_date, end_date)
        print("Сформированный DataFrame:\n", df.head())

        today = datetime.now().strftime("%Y-%m-%d")
        period_str = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
        filename = f"Табель_{telegram_id}_{period_str}.xlsx"
        excel_file = await export_to_excel(df, filename)

        await message.answer_document(
            document=BufferedInputFile(
                file=excel_file.getvalue(),
                filename=filename
            ),
            caption=f"Табель времени сотрудника за период {start_date.strftime('%d.%m.%Y')}-{end_date.strftime('%d.%m.%Y')}"
        )

    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
    finally:
        await dialog_manager.done()


async def export_current_month(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    today = date.today()
    first_day = date(today.year, today.month, 1)
    last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    await process_export_with_dates(callback.message, dialog_manager, first_day, last_day)


async def export_current_year(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    today = date.today()
    first_day = date(today.year, 1, 1)
    last_day = date(today.year, 12, 31)
    await process_export_with_dates(callback.message, dialog_manager, first_day, last_day)


async def start_custom_range_input(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.switch_to(ExportTimeTableStates.input_custom_range)


async def parse_date_input(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    try:
        date_range = message.text.strip()
        pattern = r'(\d{2})\.(\d{2})\.(\d{4})\s*-\s*(\d{2})\.(\d{2})\.(\d{4})'
        match = re.fullmatch(pattern, date_range)

        if not match:
            raise ValueError("Неверный формат даты. Используйте ДД.ММ.ГГГГ - ДД.ММ.ГГГГ")

        day1, month1, year1, day2, month2, year2 = map(int, match.groups())
        start_date = date(year1, month1, day1)
        end_date = date(year2, month2, day2)

        if start_date > end_date:
            raise ValueError("Дата начала должна быть раньше даты окончания")

        await dialog_manager.switch_to(ExportTimeTableStates.processing)
        await process_export_with_dates(
            message=message,
            dialog_manager=dialog_manager,
            start_date=start_date,
            end_date=end_date
        )

    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}\nПожалуйста, введите даты в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ")


def export_time_table_dialog():
    return Dialog(
        Window(
            Const("Выберите период для экспорта табеля времени:"),
            Button(Const("Текущий месяц"), id="export_current_month", on_click=export_current_month),
            Button(Const("Текущий год"), id="export_current_year", on_click=export_current_year),
            Button(Const("Указать период вручную"), id="export_custom_range", on_click=start_custom_range_input),
            Cancel(Const("❌ Отмена")),
            state=ExportTimeTableStates.select_period,
        ),
        Window(
            Const("Введите период в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\nНапример: 01.01.2025 - 31.12.2025"),
            MessageInput(parse_date_input),
            Cancel(Const("❌ Отмена")),
            state=ExportTimeTableStates.input_custom_range,
        ),
        Window(
            Const("Создание табеля времени..."),
            state=ExportTimeTableStates.processing,
        )
    )