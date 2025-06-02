from typing import List, Dict, Any
from psycopg2.extras import DictCursor

from data.database import Database


class WorkerOperations:
    @staticmethod
    def create_worker(db: Database, name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks=False,
                      can_receive_non_project_tasks=False, reminder_day="пятница", reminder_time="17:00:00"):
        with db.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO worker 
                (name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks, 
                 can_receive_non_project_tasks, reminder_day, reminder_time) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks,
                 can_receive_non_project_tasks, reminder_day, reminder_time)
            )
            worker_id = cursor.fetchone()[0]
            db.conn.commit()
            return worker_id

    @staticmethod
    def get_worker(db: Database, worker_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    w.id,
                    w.telegram_id,
                    w.name,
                    w.position_id,
                    w.weekly_hours,
                    w.reminder_day,
                    w.reminder_time,
                    w.can_receive_custom_tasks,
                    w.can_receive_non_project_tasks,
                    p.name as position_name
                FROM worker w
                LEFT JOIN position p ON w.position_id = p.id
                WHERE w.id = %s
            """, (worker_id,))
            worker = cursor.fetchone()
            return dict(worker) if worker else None

    @staticmethod
    def update_worker(db: Database, worker_id, name=None, position_id=None, weekly_hours=None,
                      can_receive_custom_tasks=None,
                      can_receive_non_project_tasks=None, reminder_day=None, reminder_time=None):
        with db.conn.cursor() as cursor:
            query = "UPDATE worker SET "
            updates = []
            params = []

            if name:
                updates.append("name = %s")
                params.append(name)
            if position_id:
                updates.append("position_id = %s")
                params.append(position_id)
            if weekly_hours:
                updates.append("weekly_hours = %s")
                params.append(weekly_hours)
            if can_receive_custom_tasks is not None:
                updates.append("can_receive_custom_tasks = %s")
                params.append(can_receive_custom_tasks)
            if can_receive_non_project_tasks is not None:
                updates.append("can_receive_non_project_tasks = %s")
                params.append(can_receive_non_project_tasks)
            if reminder_day:
                updates.append("reminder_day = %s")
                params.append(reminder_day)
            if reminder_time:
                updates.append("reminder_time = %s")
                params.append(reminder_time)

            query += ", ".join(updates)
            query += " WHERE id = %s"
            params.append(worker_id)

            cursor.execute(query, params)
            db.conn.commit()

    @staticmethod
    def get_all_workers(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    w.id,
                    w.telegram_id,
                    w.name,
                    w.position_id,
                    w.weekly_hours,
                    w.reminder_day,
                    w.reminder_time,
                    w.can_receive_custom_tasks,
                    w.can_receive_non_project_tasks,
                    p.name as position_name
                FROM worker w
                LEFT JOIN position p ON w.position_id = p.id
                ORDER BY w.name
            """)
            return cursor.fetchall()

    @staticmethod
    def get_worker_by_telegram_id(db: Database, telegram_id: int):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM worker WHERE telegram_id = %s", (telegram_id,)
            )
            worker = cursor.fetchone()
        if worker:
            return dict(worker)
        return None

    @staticmethod
    def get_worker_active_projects_full(db: Database, worker_id: int) -> list[dict]:
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT p.id, p.name 
                    FROM worker_active_project wap
                    JOIN project p ON wap.project_id = p.id
                    WHERE wap.worker_id = %s
                    ORDER BY p.name
                """, (worker_id,))

                projects = []
                for row in cursor.fetchall():
                    projects.append({
                        "id": row[0],
                        "name": row[1]
                    })

                return projects
            except Exception as e:
                print(f"Ошибка при получении активных проектов работника: {e}")
                return []

    @staticmethod
    def get_worker_active_projects(db: Database, worker_id: int) -> List[int]:
        with db.conn.cursor() as cursor:
            cursor.execute(
                "SELECT project_id FROM worker_active_project WHERE worker_id = %s",
                (worker_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def set_worker_active_projects(db: Database, worker_id: int, project_ids: List[int]):
        with db.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM worker_active_project WHERE worker_id = %s",
                (worker_id,)
            )
            for project_id in project_ids:
                cursor.execute(
                    "INSERT INTO worker_active_project (worker_id, project_id) VALUES (%s, %s)",
                    (worker_id, project_id)
                )
            db.conn.commit()

    @staticmethod
    def update_worker_reminder_settings(db: Database, worker_id: int, day: str, time: str):
        with db.conn.cursor() as cursor:
            cursor.execute(
                "UPDATE worker SET reminder_day = %s, reminder_time = %s WHERE id = %s",
                (day, time, worker_id)
            )
            db.conn.commit()

    @staticmethod
    def get_worker_projects(db: Database, worker_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT DISTINCT p.*
                FROM project p
                JOIN project_task pt ON p.id = pt.project_id
                JOIN time_entry te ON pt.id = te.project_task_id
                WHERE te.worker_id = %s
                ORDER BY p.name
            """, (worker_id,))
            return cursor.fetchall()
