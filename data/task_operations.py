from psycopg2.extras import DictCursor
from data.database import Database


class TaskOperations:

    @staticmethod
    def create_task(db: Database, name, stage, department, is_unique=False, is_nonproject=False, is_custom=False):
        with db.conn.cursor() as cursor:
            stage = None if stage == "None" or stage is None else stage
            department = None if department == "None" or department is None else department

            cursor.execute(
                """INSERT INTO task (name, stage, department, is_unique, is_nonproject, is_custom) 
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (name, stage, department, is_unique, is_nonproject, is_custom))
            task_id = cursor.fetchone()[0]
            db.conn.commit()
            return task_id

    @staticmethod
    def get_task(db: Database, task_id):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT id, name, stage, department, is_unique, is_nonproject, is_custom FROM task WHERE id = %s",
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
                SELECT t.id, t.name, t.stage, t.department, t.is_unique, t.is_nonproject, t.is_custom
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
                    pt.status as task_status,
                    t.is_nonproject,
                    t.is_custom
                FROM project_task pt
                JOIN project p ON pt.project_id = p.id
                JOIN task t ON pt.task_id = t.id
                LEFT JOIN font f ON pt.font_id = f.id
                WHERE pt.id = %s;
            """, (project_task_id,))
            return cursor.fetchone()

    @staticmethod
    def add_custom_task(db: Database, task_name, font_id):
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT id FROM project 
                    WHERE type = 'для кастомов' 
                    LIMIT 1;
                """)
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Не найден проект типа 'для кастомов'")
                custom_project_id = result[0]

                cursor.execute("""
                    INSERT INTO task (name, is_unique, is_custom)
                    VALUES (%s, TRUE, TRUE)
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

    @staticmethod
    def add_nonproject_task(db: Database, task_name, department):
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT id FROM project 
                    WHERE type = 'для непроектных' 
                    LIMIT 1;
                """)
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Не найден проект типа 'для непроектных'")
                nonproject_id = result[0]

                cursor.execute("""
                    INSERT INTO task (name, is_unique, is_nonproject, department)
                    VALUES (%s, TRUE, TRUE, %s)
                    RETURNING id;
                """, (task_name, department))
                task_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO project_task (project_id, task_id)
                    VALUES (%s, %s)
                    RETURNING id;
                """, (nonproject_id, task_id))
                project_task_id = cursor.fetchone()[0]

                db.conn.commit()
                return project_task_id

            except Exception as e:
                db.conn.rollback()
                print(f"Ошибка при добавлении непроектной задачи: {e}")
                return None


    @staticmethod
    def get_custom_tasks(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, stage, department, is_unique, is_nonproject, is_custom
                FROM task
                WHERE is_custom = TRUE
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_nonproject_tasks(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, stage, department, is_unique, is_nonproject, is_custom
                FROM task
                WHERE is_nonproject = TRUE
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]