from datetime import datetime
from psycopg2.extras import DictCursor

from data.database import Database


class TimeEntryOperations:
    @staticmethod
    def get_time_entries(db: Database, worker_id, project_id=None, task_id=None, font_id=None,
                         start_date: datetime = None,
                         end_date: datetime = None, limit=None):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            query = """
                    SELECT te.id, te.project_task_id, te.worker_id, te.entry_date, te.hours,
                           pt.project_id, pt.task_id, pt.font_id
                    FROM time_entry te
                    JOIN project_task pt ON te.project_task_id = pt.id
                    WHERE te.worker_id = %s
                """
            params = [worker_id]

            if project_id is not None:
                query += " AND pt.project_id = %s"
                params.append(project_id)
            if task_id is not None:
                query += " AND pt.task_id = %s"
                params.append(task_id)
            if font_id is not None:
                query += " AND pt.font_id = %s"
                params.append(font_id)
            if start_date is not None:
                query += " AND te.entry_date >= %s"
                params.append(start_date)
            if end_date is not None:
                end_date = end_date.replace(hour=23, minute=59, second=59)
                query += " AND te.entry_date <= %s"
                params.append(end_date)
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)

            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    @staticmethod
    def add_time_entry(db: Database, time_entry_data):
        with db.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO time_entry (project_task_id, worker_id, hours, comment) 
                VALUES (%s, %s, %s, %s)""",
                (time_entry_data["project_task_id"],
                 time_entry_data["worker_id"],
                 time_entry_data["hours"],
                 time_entry_data.get("comment")))
            db.conn.commit()

    @staticmethod
    def get_time_entry(db: Database, entry_id):
        try:
            with db.conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT te.id, te.project_task_id, te.worker_id, te.entry_date, te.hours,
                           pt.project_id, pt.task_id, pt.font_id, pt.comments
                    FROM time_entry te
                    JOIN project_task pt ON te.project_task_id = pt.id
                    WHERE te.id = %s
                    """,
                    (entry_id,)
                )
                result = cursor.fetchone()

            if result is None:
                return None

            return dict(result)
        except Exception as e:
            print(f"Ошибка при получении записи времени: {e}")
            return None

    @staticmethod
    def update_time_entry(db: Database, entry_id, hours):
        try:
            with db.conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """
                    UPDATE time_entry
                    SET hours = %s
                    WHERE id = %s
                    """,
                    (hours, entry_id)
                )
                db.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении записи времени: {e}")
            return False

    @staticmethod
    def delete_time_entry(db: Database, entry_id):
        with db.conn.cursor() as cursor:
            cursor.execute("DELETE FROM time_entry WHERE id = %s", (entry_id,))
            db.conn.commit()
            return cursor.rowcount > 0
