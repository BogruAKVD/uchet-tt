import os
from typing import Optional, List
import psycopg2
from psycopg2.extras import DictCursor
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# Database credentials
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


class ProjectType(Enum):
    PLANNED = "плановый"
    CLIENT = "клиентский"
    CUSTOM = "кастом"
    NONPROJECT = "непроектный"


class Status(Enum):
    IN_PROGRESS = "в работе"
    COMPLETED = "завершён"
    ON_HOLD = "на паузе"
    CANCELLED = "отменен"


class DepartmentType(Enum):
    FONT = "шрифтовой"
    TECHNICAL = "технический"
    GRAPHIC = "графический"


class Stage(Enum):
    PREPARATION = "подготовка"
    DRAWING_STRAIGHT = "отрисовка прямые"
    DRAWING_ITALIC = "отрисовка италики"
    DRAWING_CAPITAL = "отрисовка капитель"
    TECHNICAL = "техничка"
    FORMATTING = "оформление"


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

    def drop_all_tables(self):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT 'DROP TABLE IF EXISTS ' || n.nspname || '.' || c.relname || ' CASCADE;'
                    FROM pg_catalog.pg_class AS c
                    LEFT JOIN pg_catalog.pg_namespace AS n
                    ON n.oid = c.relnamespace
                    WHERE relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                    AND pg_catalog.pg_table_is_visible(c.oid);
                """)
                drop_queries = cursor.fetchall()

                for query in drop_queries:
                    cursor.execute(query[0])
                self.conn.commit()
                print("Все таблицы успешно удалены.")
            except Exception as e:
                self.conn.rollback()
                print(f"Ошибка при удалении таблиц: {e}")

    def create_tables(self):
        with self.conn.cursor() as cursor:
            cursor.execute("BEGIN;")
            try:
                self.create_position_table(cursor)
                self.create_font_table(cursor)
                self.create_worker_table(cursor)
                self.create_project_table(cursor)
                self.create_task_table(cursor)
                self.create_project_task_table(cursor)
                self.create_time_entry_table(cursor)
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                print(f"Ошибка при создании таблиц: {e}")

    def create_worker_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                name TEXT NOT NULL,
                position_id INTEGER REFERENCES position(id),
                weekly_hours INTEGER CHECK (weekly_hours >= 0),
                can_receive_custom_tasks BOOLEAN DEFAULT FALSE,
                can_receive_non_project_tasks BOOLEAN DEFAULT FALSE
            );
        """)

    def create_font_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS font (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
        """)

    def create_position_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                department_type TEXT NOT NULL CHECK (department_type IN ('шрифтовой', 'технический', 'графический')),
                UNIQUE (name, department_type)
            );
        """)

    def create_project_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('плановый', 'клиентский', 'кастом', 'непроектный')),
                status TEXT NOT NULL DEFAULT 'в работе' CHECK (status IN ('в работе', 'завершён', 'на паузе', 'отменен'))
            );
        """)

    def create_task_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                stage TEXT NULL,
                department_type TEXT NULL,
                is_unique BOOLEAN NOT NULL DEFAULT FALSE
            );
        """)

    def create_project_task_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_task (
                project_id INTEGER REFERENCES project(id),
                task_id INTEGER REFERENCES task(id),
                font_id INTEGER REFERENCES font(id),
                comments TEXT,
                PRIMARY KEY (project_id, task_id, font_id)
            );
        """)

    def create_time_entry_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entry (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES project(id),
                worker_id INTEGER NOT NULL REFERENCES worker(id),
                task_id INTEGER NOT NULL REFERENCES task(id),
                entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
                hours DOUBLE PRECISION NOT NULL CHECK (hours > 0)
            );
        """)

    # Worker methods
    def create_worker(self, name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks=False,
                      can_receive_non_project_tasks=False):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO worker (name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks, can_receive_non_project_tasks) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks, can_receive_non_project_tasks)
            )
            worker_id = cursor.fetchone()[0]
            self.conn.commit()
            return worker_id

    def get_worker(self, worker_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT w.id, w.telegram_id, w.name, p.name AS position_name, w.weekly_hours, 
                       w.can_receive_custom_tasks, w.can_receive_non_project_tasks
                FROM worker w
                LEFT JOIN position p ON w.position_id = p.id
                WHERE w.id = %s
            """, (worker_id,))
            worker = cursor.fetchone()
            return dict(worker) if worker else None

    def update_worker(self, worker_id, name=None, position_id=None, weekly_hours=None, can_receive_custom_tasks=None,
                      can_receive_non_project_tasks=None):
        with self.conn.cursor() as cursor:
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

            query += ", ".join(updates)
            query += " WHERE id = %s"
            params.append(worker_id)

            cursor.execute(query, params)
            self.conn.commit()

    # Position methods
    def create_position(self, name, department_type):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO position (name, department_type) VALUES (%s, %s) RETURNING id",
                (name, department_type)
            )
            position_id = cursor.fetchone()[0]
            self.conn.commit()
            return position_id

    def get_position(self, position_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM position WHERE id = %s",
                (position_id,)
            )
            return cursor.fetchone()

    def get_all_positions(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM position")
            return cursor.fetchall()

    def get_positions_by_department_type(self, department_type):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM position WHERE department_type = %s", (department_type,)
            )
            return cursor.fetchall()

    # Project methods
    def create_project(self, name: str, project_type: str, tasks_with_fonts: List[dict] = None,
                       status: str = Status.IN_PROGRESS.value) -> int:
        #TODO Add custom tasks
        """Создает новый проект с возможностью привязки задач к шрифтам по имени шрифта.

        Args:
            name: Название проекта
            project_type: Тип проекта (из ProjectType)
            tasks_with_fonts: Список словарей вида [{
                'task_id': int,
                'font_name': Optional[str],
                'comments': Optional[str]
            }]
            status: Статус проекта (из Status)

        Returns:
            ID созданного проекта
        """
        print(tasks_with_fonts)
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO project (name, type, status) VALUES (%s, %s, %s) RETURNING id",
                    (name, project_type, status))
                project_id = cursor.fetchone()[0]

                if tasks_with_fonts:
                    font_names = {task['font_name'] for task in tasks_with_fonts
                                  if task.get('font_name') is not None}

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

                self.conn.commit()
                return project_id
            except Exception as e:
                self.conn.rollback()
                raise Exception(f"Ошибка при создании проекта: {e}")

    def update_project(self, project_id: int, new_name: Optional[str] = None,
                       new_type: Optional[str] = None, new_status: Optional[str] = None,
                       tasks_with_fonts: Optional[List[dict]] = None) -> None:
        """Обновляет информацию о проекте, включая привязки задач к шрифтам.

        Args:
            project_id: ID проекта для обновления
            new_name: Новое название проекта (если нужно изменить)
            new_type: Новый тип проекта (если нужно изменить)
            new_status: Новый статус проекта (если нужно изменить)
            tasks_with_fonts: Список словарей с задачами и шрифтами:
                [{'task_id': int, 'font_id': Optional[int], 'comments': Optional[str]}]
                Если None - связи задач не изменяются.
                Если пустой список - все связи удаляются.
                Если список с задачами - заменяет текущие связи.
        """
        with self.conn.cursor() as cursor:
            try:
                # Обновляем основную информацию о проекте
                updates = []
                params = []

                if new_name is not None:
                    updates.append("name = %s")
                    params.append(new_name)
                if new_type is not None:
                    updates.append("type = %s")
                    params.append(new_type)
                if new_status is not None:
                    updates.append("status = %s")
                    params.append(new_status)

                if updates:
                    update_query = "UPDATE project SET " + ", ".join(updates) + " WHERE id = %s"
                    params.append(project_id)
                    cursor.execute(update_query, params)

                if tasks_with_fonts is not None:
                    cursor.execute(
                        "DELETE FROM project_task WHERE project_id = %s",
                        (project_id,)
                    )

                    if tasks_with_fonts:
                        for task_info in tasks_with_fonts:
                            cursor.execute(
                                """INSERT INTO project_task 
                                (project_id, task_id, font_id, comments) 
                                VALUES (%s, %s, %s, %s)""",
                                (project_id,
                                 task_info['task_id'],
                                 task_info.get('font_id'),
                                 task_info.get('comments'))
                            )

                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                raise Exception(f"Ошибка при обновлении проекта: {e}")

    def get_project(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM project WHERE id = %s",
                (project_id,)
            )
            return cursor.fetchone()

    def get_project_with_tasks_and_fonts(self, project_id: int) -> Optional[dict]:
        """Возвращает полную информацию о проекте, включая задачи с привязанными шрифтами."""
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            try:
                # Получаем основную информацию о проекте
                cursor.execute(
                    "SELECT * FROM project WHERE id = %s",
                    (project_id,)
                )
                project = cursor.fetchone()

                if not project:
                    return None

                # Получаем все задачи проекта с информацией о шрифтах
                cursor.execute("""
                    SELECT 
                        t.id as task_id, 
                        t.name as task_name, 
                        t.stage, 
                        t.department_type,
                        t.is_unique,
                        f.id as font_id, 
                        f.name as font_name, 
                        pt.comments
                    FROM project_task pt
                    JOIN task t ON pt.task_id = t.id
                    LEFT JOIN font f ON pt.font_id = f.id
                    WHERE pt.project_id = %s
                    ORDER BY t.name
                """, (project_id,))

                tasks = cursor.fetchall()

                return {
                    'project': dict(project),
                    'tasks': [dict(task) for task in tasks]
                }
            except Exception as e:
                raise Exception(f"Ошибка при получении информации о проекте: {e}")

    # Task methods
    def create_task(self, name, stage, department_type, is_unique=False):
        with self.conn.cursor() as cursor:
            stage = None if stage == "None" or stage is None else stage
            department_type = None if department_type == "None" or department_type is None else department_type

            cursor.execute(
                """INSERT INTO task (name, stage, department_type, is_unique) 
                VALUES (%s, %s, %s, %s) RETURNING id""",
                (name, stage, department_type, is_unique))
            task_id = cursor.fetchone()[0]
            self.conn.commit()
            return task_id

    def get_task(self, task_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT id, name, stage, department_type, is_unique FROM task WHERE id = %s",
                (task_id,)
            )
            return cursor.fetchone()

    def update_task(self, task_id, name=None, stage=None, department_type=None, is_unique=None):
        with self.conn.cursor() as cursor:
            query = "UPDATE task SET "
            updates = []
            params = []

            if name:
                updates.append("name = %s")
                params.append(name)
            if stage is not None:
                updates.append("stage = %s")
                params.append(stage)
            if department_type is not None:
                updates.append("department_type = %s")
                params.append(department_type)
            if is_unique is not None:
                updates.append("is_unique = %s")
                params.append(is_unique)

            query += ", ".join(updates)
            query += " WHERE id = %s"
            params.append(task_id)

            cursor.execute(query, params)
            self.conn.commit()

    # Time entry methods
    def add_time_entry(self, project_id, worker_id, task_id, hours, entry_date=None):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO time_entry 
                (project_id, worker_id, task_id, hours, entry_date)
                VALUES (%s, %s, %s, %s, COALESCE(%s, CURRENT_DATE))""",
                (project_id, worker_id, task_id, hours, entry_date)
            )
            self.conn.commit()

    def get_time_entries(self, worker_id, project_id=None):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            if project_id:
                cursor.execute(
                    """SELECT * FROM time_entry 
                    WHERE worker_id = %s AND project_id = %s""",
                    (worker_id, project_id)
                )
            else:
                cursor.execute(
                    """SELECT * FROM time_entry 
                    WHERE worker_id = %s""",
                    (worker_id,)
                )
            return cursor.fetchall()

    def get_time_entries_by_project(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT te.*, w.name as worker_name, t.name as task_name
                FROM time_entry te
                JOIN worker w ON te.worker_id = w.id
                JOIN task t ON te.task_id = t.id
                WHERE te.project_id = %s
                ORDER BY te.entry_date DESC
            """, (project_id,))
            return cursor.fetchall()

    # Font methods
    def create_font(self, name):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO font (name) VALUES (%s) RETURNING id",
                (name,)
            )
            font_id = cursor.fetchone()[0]
            self.conn.commit()
            return font_id

    def get_font(self, font_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM font WHERE id = %s",
                (font_id,)
            )
            return cursor.fetchone()

    def get_all_fonts(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM font ORDER BY name")
            return cursor.fetchall()

    # Other methods
    def get_worker_projects(self, worker_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT DISTINCT p.*
                FROM project p
                JOIN time_entry te ON p.id = te.project_id
                WHERE te.worker_id = %s
                ORDER BY p.name
            """, (worker_id,))
            return cursor.fetchall()

    def get_worker_project_tasks(self, worker_id, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT DISTINCT t.*
                FROM task t
                JOIN time_entry te ON t.id = te.task_id
                WHERE te.worker_id = %s AND te.project_id = %s
                ORDER BY t.name
            """, (worker_id, project_id))
            return cursor.fetchall()

    def get_project_tasks(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """SELECT t.*, f.id as font_id, f.name as font_name, pt.comments 
                FROM task t
                JOIN project_task pt ON t.id = pt.task_id
                LEFT JOIN font f ON pt.font_id = f.id
                WHERE pt.project_id = %s""",
                (project_id,)
            )
            return cursor.fetchall()

    def get_project_workers(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT DISTINCT w.*, p.name as position_name
                FROM worker w
                JOIN position p ON w.position_id = p.id
                JOIN time_entry te ON w.id = te.worker_id
                WHERE te.project_id = %s
                ORDER BY w.name
            """, (project_id,))
            return cursor.fetchall()

    def get_task_by_name(self, task_name):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM task WHERE name = %s",
                (task_name,)
            )
            return cursor.fetchone()

    def get_all_tasks(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM task ORDER BY name"
            )
            return cursor.fetchall()

    def get_all_workers(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT w.*, p.name as position_name
                FROM worker w
                LEFT JOIN position p ON w.position_id = p.id
                ORDER BY w.name
            """)
            return cursor.fetchall()

    def get_all_projects(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM project ORDER BY name",
            )
            return cursor.fetchall()

    def get_worker_by_telegram_id(self, telegram_id: int):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM worker WHERE telegram_id = %s", (telegram_id,)
            )
            worker = cursor.fetchone()
        return worker

    def get_worker_names(self, worker_ids):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, name FROM worker WHERE id IN %s
                """,
                (tuple(worker_ids),)
            )
            return {row['id']: row['name'] for row in cursor.fetchall()}

    def get_task_names(self, task_ids):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, name FROM task WHERE id IN %s
                """,
                (tuple(task_ids),)
            )
            return {row['id']: row['name'] for row in cursor.fetchall()}

    def get_tasks_by_stage(self, stage: str):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT t.id, t.name, t.stage, t.department_type
                FROM task t
                WHERE t.stage IS NOT DISTINCT FROM %s
                ORDER BY t.name
            """, (stage,))
            return cursor.fetchall()

    def add_task_to_project(self, project_id, task_id, font_id=None, comments=None):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO project_task (project_id, task_id, font_id, comments) VALUES (%s, %s, %s, %s)",
                (project_id, task_id, font_id, comments)
            )
            self.conn.commit()

    def remove_task_from_project(self, project_id, task_id, font_id=None):
        with self.conn.cursor() as cursor:
            if font_id:
                cursor.execute(
                    "DELETE FROM project_task WHERE project_id = %s AND task_id = %s AND font_id = %s",
                    (project_id, task_id, font_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM project_task WHERE project_id = %s AND task_id = %s AND font_id IS NULL",
                    (project_id, task_id)
                )
            self.conn.commit()

    def get_project_task_info(self, project_id, task_id, font_id=None):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            if font_id:
                cursor.execute("""
                    SELECT pt.*, t.name as task_name, f.name as font_name
                    FROM project_task pt
                    JOIN task t ON pt.task_id = t.id
                    LEFT JOIN font f ON pt.font_id = f.id
                    WHERE pt.project_id = %s AND pt.task_id = %s AND pt.font_id = %s
                """, (project_id, task_id, font_id))
            else:
                cursor.execute("""
                    SELECT pt.*, t.name as task_name, NULL as font_name
                    FROM project_task pt
                    JOIN task t ON pt.task_id = t.id
                    WHERE pt.project_id = %s AND pt.task_id = %s AND pt.font_id IS NULL
                """, (project_id, task_id))
            return cursor.fetchone()

    def close(self):
        self.conn.close()