from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
import pandas as pd
from io import BytesIO
import psycopg2
from datetime import datetime, date
import calendar


class ExportTimeTableStates(StatesGroup):
    processing = State()


async def get_worker_time_data(worker_telegram_id: int, db_conn) -> pd.DataFrame:
    from datetime import date
    today = date.today()
    year = today.year
    all_dates = [date(year, m, d)
                 for m in range(1, 13)
                 for d in range(1, calendar.monthrange(year, m)[1] + 1)]
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
        """, (worker_telegram_id, date(year, 1, 1), date(year, 12, 31)))
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
                **{date: '' for date in date_columns}
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
            """, (worker_telegram_id, date(year, 1, 1), date(year, 12, 31), project_id))

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
                    **{date: data['entries'].get(date, '') for date in date_columns}
                })

    column_order = ['Тип', 'project_task_id', 'Проект', 'Шрифт', 'Задача'] + date_columns
    df = pd.DataFrame(result_rows)
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
            worksheet.set_column(col_num, col_num, 12 if col == 'project_task_id' else 18 if col in ['Проект', 'Шрифт', 'Задача'] else 8)

        for row_idx in range(len(df)):
            row = df.iloc[row_idx]
            row_type = row['Тип']

            if row_type == 'Проект':
                fmt = project_format
            else:
                fmt = task_format

            for col_idx, value in enumerate(row):
                if row_type == 'Задача' and df.columns[col_idx] not in ['Тип', 'project_task_id', 'Проект', 'Шрифт', 'Задача'] and value != '':
                    worksheet.write(row_idx + 1, col_idx, float(value), hour_format)
                else:
                    worksheet.write(row_idx + 1, col_idx, value, fmt)

    output.seek(0)
    return output



async def process_export(callback: CallbackQuery, button: Button,
                         dialog_manager: DialogManager):
    try:
        db = dialog_manager.middleware_data['db']
        telegram_id = dialog_manager.event.from_user.id

        df = await get_worker_time_data(telegram_id, db.conn)
        print("Сформированный DataFrame:\n", df.head())

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"Табель_{telegram_id}_{today}.xlsx"
        excel_file = await export_to_excel(df, filename)

        await callback.message.answer_document(
            document=BufferedInputFile(
                file=excel_file.getvalue(),
                filename=filename
            ),
            caption=f"Табель времени сотрудника"
        )

    except Exception as e:
        await callback.message.answer(f"Ошибка: {str(e)}")
    finally:
        await dialog_manager.done()

def export_time_table_dialog():
    return Dialog(
        Window(
            Const("Создание табеля времени...\n\nБудет создан файл с данными за текущий год."),
            Button(Const("✅ Создать табель"), id="export", on_click=process_export),
            Cancel(Const("❌ Отмена")),
            state=ExportTimeTableStates.processing,
        )
    )