from psycopg2.extras import DictCursor

from data.database import Database


class TaskOperations:

    @staticmethod
    def create_task(db: Database, name, stage, department_type, is_unique=False):
        with db.conn.cursor() as cursor:
            stage = None if stage == "None" or stage is None else stage
            department_type = None if department_type == "None" or department_type is None else department_type

            cursor.execute(
                """INSERT INTO task (name, stage, department_type, is_unique) 
                VALUES (%s, %s, %s, %s) RETURNING id""",
                (name, stage, department_type, is_unique))
            task_id = cursor.fetchone()[0]
            db.conn.commit()
            return task_id

    @staticmethod
    def get_task(db: Database, task_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT id, name, stage, department_type, is_unique FROM task WHERE id = %s",
                (task_id,)
            )
            return cursor.fetchone()

    @staticmethod
    def get_task_by_id(db: Database, task_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM task WHERE id = %s",
                (task_id,)
            )
            result = dict(cursor.fetchone())
            print(result)
            return result

    @staticmethod
    def get_tasks_by_stage(db: Database, stage: str):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            stage = None if stage == "None" else stage

            cursor.execute("""
                SELECT t.id, t.name, t.stage, t.department_type
                FROM task t
                WHERE t.stage IS NOT DISTINCT FROM %s
                ORDER BY t.name
            """, (stage,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_project_task_info(db: Database, project_task_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    p.name as project_name,
                    t.name as task_name,
                    f.name as font_name,
                    pt.status as task_status
                FROM project_task pt
                JOIN project p ON pt.project_id = p.id
                JOIN task t ON pt.task_id = t.id
                LEFT JOIN font f ON pt.font_id = f.id
                WHERE pt.id = %s;
            """, (project_task_id,))
            return cursor.fetchone()

    @staticmethod
    def add_custom_task(db: Database, task_name, font_id, custom_project_id=None):
        with db.conn.cursor() as cursor:
            try:
                if custom_project_id is None:
                    cursor.execute("""
                        SELECT id FROM project 
                        WHERE type = 'для кастома' 
                        LIMIT 1;
                    """)
                    result = cursor.fetchone()
                    if not result:
                        raise ValueError("Не найден проект типа 'для кастома'")
                    custom_project_id = result[0]

                cursor.execute("""
                    INSERT INTO task (name, is_unique)
                    VALUES (%s, TRUE)
                    RETURNING id;
                """, (task_name,))
                task_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO project_task (project_id, task_id, font_id)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (custom_project_id, task_id, font_id))
                project_task_id = cursor.fetchone()[0]

                db.conn.commit()
                return project_task_id

            except Exception as e:
                db.conn.rollback()
                print(f"Ошибка при добавлении кастомной задачи: {e}")
                return None
