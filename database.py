import os
from typing import Optional

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
        """Удаление всех таблиц в базе данных."""
        with self.conn.cursor() as cursor:
            try:
                # Получение списка таблиц
                cursor.execute("""
                    SELECT 'DROP TABLE IF EXISTS ' || n.nspname || '.' || c.relname || ' CASCADE;'
                    FROM pg_catalog.pg_class AS c
                    LEFT JOIN pg_catalog.pg_namespace AS n
                    ON n.oid = c.relnamespace
                    WHERE relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                    AND pg_catalog.pg_table_is_visible(c.oid);
                """)
                drop_queries = cursor.fetchall()

                # Выполнение запросов удаления таблиц
                for query in drop_queries:
                    cursor.execute(query[0])
                self.conn.commit()
                print("Все таблицы успешно удалены.")
            except Exception as e:
                self.conn.rollback()
                print(f"Ошибка при удалении таблиц: {e}")

    def create_tables(self):
        """Создание всех таблиц."""
        with self.conn.cursor() as cursor:
            cursor.execute("BEGIN;")
            try:
                self.create_position_table(cursor)
                self.create_worker_table(cursor)
                self.create_project_table(cursor)
                self.create_task_table(cursor)
                self.create_project_worker_table(cursor)
                self.create_project_task_table(cursor)
                self.create_time_entry_table(cursor)
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                print(f"Ошибка при создании таблиц: {e}")

    def create_worker_table(self, cursor):
        """Создание таблицы worker."""
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

    def create_position_table(self, cursor):
        """Создание таблицы position."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                department_type TEXT NOT NULL CHECK (department_type IN ('шрифтовой', 'технический', 'графический')),
                UNIQUE (name, department_type)
            );
        """)

    def create_project_table(self, cursor):
        """Создание таблицы project."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('плановый', 'клиентский', 'кастом', 'непроектный')),
                status TEXT NOT NULL DEFAULT 'в работе' CHECK (status IN ('в работе', 'завершён', 'на паузе', 'отменен'))
            );
        """)

    def create_task_table(self, cursor):
        """Создание таблицы task."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                stage TEXT NULL,
                department_type TEXT NULL,
                is_unique BOOLEAN NOT NULL DEFAULT FALSE
            );
        """)

    def create_project_worker_table(self, cursor):
        """Создание таблицы project_worker."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_worker (
                project_id INTEGER REFERENCES project(id),
                worker_id INTEGER REFERENCES worker(id),
                PRIMARY KEY (project_id, worker_id)
            );
        """)

    def create_project_task_table(self, cursor):
        """Создание таблицы project_task."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_task (
                project_id INTEGER REFERENCES project(id),
                task_id INTEGER REFERENCES task(id),
                comments TEXT,
                PRIMARY KEY (project_id, task_id)
            );
        """)

    def create_time_entry_table(self, cursor):
        """Создание таблицы time_entry."""
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
                SELECT w.id, w.telegram_id, w.name, p.name AS position_name, w.weekly_hours, w.can_receive_custom_tasks, w.can_receive_non_project_tasks
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
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT position FROM positions WHERE department_type = %s", (department_type,)
            )
            return [row[0] for row in cursor.fetchall()]

    # Project methods
    def create_project(self, name, project_type, task_ids, worker_ids, status=Status.IN_PROGRESS.value):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO project (name, type, status) VALUES (%s, %s, %s) RETURNING id",
                (name, project_type, status)
            )
            project_id = cursor.fetchone()[0]

            for task_id in task_ids:
                cursor.execute(
                    "INSERT INTO project_task (project_id, task_id) VALUES (%s, %s)",
                    (project_id, task_id)
                )

            for worker_id in worker_ids:
                cursor.execute(
                    "INSERT INTO project_worker (project_id, worker_id) VALUES (%s, %s)",
                    (project_id, worker_id)
                )

            self.conn.commit()
            return project_id

    def update_project(self, project_id, new_name=None, new_type=None, new_tasks=None, new_workers=None,
                       new_status=None):
        with self.conn.cursor() as cursor:
            if new_name:
                cursor.execute(
                    "UPDATE project SET name = %s WHERE id = %s",
                    (new_name, project_id)
                )

            if new_type:
                cursor.execute(
                    "UPDATE project SET type = %s WHERE id = %s",
                    (new_type, project_id)
                )

            if new_status:
                cursor.execute(
                    "UPDATE project SET status = %s WHERE id = %s",
                    (new_status, project_id)
                )

            if new_tasks is not None:
                cursor.execute(
                    "DELETE FROM project_task WHERE project_id = %s",
                    (project_id,)
                )
                for task_id in new_tasks:
                    cursor.execute(
                        "INSERT INTO project_task (project_id, task_id) VALUES (%s, %s)",
                        (project_id, task_id)
                    )

            if new_workers is not None:
                cursor.execute(
                    "DELETE FROM project_worker WHERE project_id = %s",
                    (project_id,)
                )
                for worker_id in new_workers:
                    cursor.execute(
                        "INSERT INTO project_worker (project_id, worker_id) VALUES (%s, %s)",
                        (project_id, worker_id)
                    )

            self.conn.commit()

    def get_project(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM project WHERE id = %s",
                (project_id,)
            )
            return cursor.fetchone()

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

    # Getter methods
    def get_worker_projects(self, worker_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """SELECT p.* FROM project p
                JOIN project_worker pw ON p.id = pw.project_id
                WHERE pw.worker_id = %s""",
                (worker_id,)
            )
            return cursor.fetchall()

    def get_worker_project_tasks(self, worker_id, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """SELECT t.* FROM task t
                JOIN project_task pt ON t.id = pt.task_id
                JOIN project p ON pt.project_id = p.id
                JOIN project_worker pw ON p.id = pw.project_id
                WHERE pw.worker_id = %s AND p.id = %s""",
                (worker_id, project_id)
            )
            return cursor.fetchall()

    def get_project_tasks(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """SELECT t.* FROM task t
                JOIN project_task pt ON t.id = pt.task_id
                WHERE pt.project_id = %s""",
                (project_id,)
            )
            return cursor.fetchall()

    def get_project_workers(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """SELECT w.* FROM worker w
                JOIN project_worker pw ON w.id = pw.worker_id
                WHERE pw.project_id = %s""",
                (project_id,)
            )
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
                "SELECT * FROM task"
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
                "SELECT * FROM project",
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
                SELECT name FROM worker WHERE id IN %s
                """,
                (tuple(worker_ids),)
            )
            worker_names = [row['name'] for row in cursor.fetchall()]
        return worker_names

    def get_task_names(self, task_ids):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """
                SELECT name FROM task WHERE id IN %s
                """,
                (tuple(task_ids),)
            )
            task_names = [row['name'] for row in cursor.fetchall()]
        return task_names

    def get_tasks_by_stage(self, stage: str):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT t.id, t.name, t.stage, t.department_type
                FROM task t
                WHERE t.stage IS NOT DISTINCT FROM %s
                ORDER BY t.name
            """, (stage,))
            return cursor.fetchall()

    def add_task_to_project(self, project_id, task_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO project_task (project_id, task_id) VALUES (%s, %s)",
                (project_id, task_id)
            )
            self.conn.commit()