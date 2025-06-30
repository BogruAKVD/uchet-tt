from typing import List, Dict, Any, Optional
from psycopg2.extras import DictCursor

from data.task_operations import TaskOperations
from data.models import Status
from data.database import Database


class ProjectOperations:
    @staticmethod
    def create_project(db: Database, name: str, project_type: str, tasks_with_fonts: List[dict] = None,
                       unique_tasks_with_fonts: List[dict] = None,
                       status: str = Status.IN_PROGRESS.value) -> int:
        with db.conn.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO project (name, type, status) VALUES (%s, %s, %s) RETURNING id",
                    (name, project_type, status))
                project_id = cursor.fetchone()[0]

                font_names = set()

                if tasks_with_fonts:
                    font_names.update(task['font_name'] for task in tasks_with_fonts
                                      if task.get('font_name') is not None)

                if unique_tasks_with_fonts:
                    font_names.update(task['font_name'] for task in unique_tasks_with_fonts
                                      if task.get('font_name') is not None)

                font_name_to_id = {}
                for font_name in font_names:
                    cursor.execute(
                        "SELECT id FROM font WHERE name = %s",
                        (font_name,))
                    font_row = cursor.fetchone()

                    if font_row:
                        font_id = font_row[0]
                    else:
                        cursor.execute(
                            "INSERT INTO font (name) VALUES (%s) RETURNING id",
                            (font_name,))
                        font_id = cursor.fetchone()[0]

                    font_name_to_id[font_name] = font_id

                if tasks_with_fonts:
                    for task_info in tasks_with_fonts:
                        font_id = None
                        if task_info.get('font_name') is not None:
                            font_id = font_name_to_id.get(task_info['font_name'])

                        cursor.execute(
                            """INSERT INTO project_task 
                            (project_id, task_id, font_id, comments) 
                            VALUES (%s, %s, %s, %s)""",
                            (project_id,
                             task_info['task_id'],
                             font_id,
                             task_info.get('comments'))
                        )

                if unique_tasks_with_fonts:
                    for unique_task in unique_tasks_with_fonts:
                        task_id = TaskOperations.create_task(
                            db,
                            name=unique_task['name'],
                            stage=unique_task.get('stage'),
                            department=unique_task.get('department'),
                            is_unique=True
                        )

                        font_id = None
                        if unique_task.get('font_name') is not None:
                            font_id = font_name_to_id.get(unique_task['font_name'])

                        cursor.execute(
                            """INSERT INTO project_task 
                            (project_id, task_id, font_id, comments) 
                            VALUES (%s, %s, %s, %s)""",
                            (project_id,
                             task_id,
                             font_id,
                             unique_task.get('comments'))
                        )

                db.conn.commit()
                return project_id
            except Exception as e:
                db.conn.rollback()
                raise Exception(f"Ошибка при создании проекта: {e}")

    @staticmethod
    def get_project(db: Database, project_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM project WHERE id = %s",
                (project_id,)
            )
            return cursor.fetchone()

    @staticmethod
    def get_all_projects(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM project ORDER BY name",
            )
            return cursor.fetchall()

    @staticmethod
    def get_active_projects(db: Database) -> List[Dict[str, Any]]:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, type, status 
                FROM project 
                WHERE status = 'в работе'
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_project_by_id(db: Database, project_id: int) -> Dict[str, Any]:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, type, status 
                FROM project 
                WHERE id = %s
            """, (project_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def get_project_tasks(db: Database, project_id: int) -> List[Dict[str, Any]]:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    pt.id,
                    t.name,
                    t.stage,
                    t.department,
                    pt.status,
                    f.name as font_name
                FROM project_task pt
                JOIN task t ON pt.task_id = t.id
                LEFT JOIN font f ON pt.font_id = f.id
                WHERE pt.project_id = %s
                ORDER BY t.stage, t.department, t.name
            """, (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_project_task(db: Database, project_task_id: int) -> Dict[str, Any]:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, status FROM project_task WHERE id = %s
            """, (project_task_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def get_project_name(db: Database, project_id: int) -> str:
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT name FROM project WHERE id = %s
                """, (project_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
            except Exception as e:
                print(f"Ошибка при получении названия проекта: {e}")
                return ""

    @staticmethod
    def get_custom_project(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                 SELECT id, name FROM project 
                 WHERE type = 'для кастомов' 
                 LIMIT 1;
             """)
            return dict(cursor.fetchone())

    @staticmethod
    def get_nonproject_project(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                 SELECT id, name FROM project 
                 WHERE type = 'для непроектных' 
                 LIMIT 1;
             """)
            return dict(cursor.fetchone())

    @staticmethod
    def get_tasks_for_project(db: Database, project_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT pt.id, t.name, f.name as font_name
                FROM project_task pt
                JOIN task t ON pt.task_id = t.id
                LEFT JOIN font f ON pt.font_id = f.id
                WHERE pt.project_id = %s;
            """, (project_id,))
            return cursor.fetchall()

    @staticmethod
    def get_available_projects(db: Database, worker_id: int) -> List[Dict[str, Any]]:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT p.id, p.name 
                FROM project p
                WHERE p.status = 'в работе' AND p.type != 'для кастома'
                ORDER BY p.name
            """, (worker_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_project_tasks_by_stage(db: Database, project_id: int, stage: Optional[str]) -> List[Dict[str, Any]]:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            if stage is None:
                cursor.execute("""
                        SELECT 
                            pt.id,
                            t.name,
                            t.stage,
                            t.department,
                            pt.status,
                            f.name as font_name
                        FROM project_task pt
                        JOIN task t ON pt.task_id = t.id
                        LEFT JOIN font f ON pt.font_id = f.id
                        WHERE pt.project_id = %s AND t.stage IS NULL
                        ORDER BY t.department, t.name
                    """, (project_id,))
            else:
                cursor.execute("""
                        SELECT 
                            pt.id,
                            t.name,
                            t.stage,
                            t.department,
                            pt.status,
                            f.name as font_name
                        FROM project_task pt
                        JOIN task t ON pt.task_id = t.id
                        LEFT JOIN font f ON pt.font_id = f.id
                        WHERE pt.project_id = %s AND t.stage = %s
                        ORDER BY t.department, t.name
                    """, (project_id, stage))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def complete_task(db: Database, project_task_id: int) -> None:
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                        UPDATE project_task
                        SET status = 'завершён'
                        WHERE id = %s
                        RETURNING id
                    """, (project_task_id,))
                db.conn.commit()
            except Exception as e:
                db.conn.rollback()
                raise Exception(f"Ошибка при завершении задачи: {e}")

    @staticmethod
    def update_task_status(db: Database, project_task_id: int, status: str) -> None:
        with db.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE project_task
                SET status = %s
                WHERE id = %s
            """, (status, project_task_id))
            db.conn.commit()

    @staticmethod
    def complete_stage_tasks(db: Database, project_id: int, stage: Optional[str]) -> None:
        with db.conn.cursor() as cursor:
            try:
                if stage is None:
                    cursor.execute("""
                            UPDATE project_task pt
                            SET status = 'завершён'
                            FROM task t
                            WHERE pt.task_id = t.id
                            AND pt.project_id = %s
                            AND t.stage IS NULL
                            AND pt.status != 'завершён'
                        """, (project_id,))
                else:
                    cursor.execute("""
                            UPDATE project_task pt
                            SET status = 'завершён'
                            FROM task t
                            WHERE pt.task_id = t.id
                            AND pt.project_id = %s
                            AND t.stage = %s
                            AND pt.status != 'завершён'
                        """, (project_id, stage))
                db.conn.commit()
            except Exception as e:
                db.conn.rollback()
                raise Exception(f"Ошибка при завершении задач этапа: {e}")

    @staticmethod
    def incomplete_stage_tasks(db: Database, project_id: int, stage: Optional[str]) -> None:
        with db.conn.cursor() as cursor:
            if stage is None:
                cursor.execute("""
                    UPDATE project_task pt
                    SET status = 'в процессе'
                    FROM task t
                    WHERE pt.task_id = t.id
                    AND pt.project_id = %s
                    AND t.stage IS NULL
                """, (project_id,))
            else:
                cursor.execute("""
                    UPDATE project_task pt
                    SET status = 'в процессе'
                    FROM task t
                    WHERE pt.task_id = t.id
                    AND pt.project_id = %s
                    AND t.stage = %s
                """, (project_id, stage))
            db.conn.commit()

    @staticmethod
    def update_project_status(db: Database, project_id: int, new_status: str) -> None:
        with db.conn.cursor() as cursor:
            valid_statuses = [status.value for status in Status]
            if new_status not in valid_statuses:
                raise ValueError(f"Недопустимый статус проекта: {new_status}")

            cursor.execute("""
                UPDATE project
                SET status = %s
                WHERE id = %s
            """, (new_status, project_id))

            if new_status==Status.COMPLETED.value:
                cursor.execute("""
                    UPDATE project_task
                    SET status = 'завершён'
                    WHERE project_id = %s
                    AND status != 'завершён'
                """, (project_id,))

            db.conn.commit()

    @staticmethod
    def get_project_stages(db: Database, project_id: int) -> List[str]:
        with db.conn.cursor() as cursor:
            cursor.execute("""
                    SELECT DISTINCT t.stage
                    FROM project_task pt
                    JOIN task t ON pt.task_id = t.id
                    WHERE pt.project_id = %s
                    AND t.stage IS NOT NULL
                """, (project_id,))
            return [row[0] for row in cursor.fetchall()]
