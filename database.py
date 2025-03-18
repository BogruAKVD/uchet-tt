import os
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
    CLIENT = "клиентский"
    PROJECT = "проектный"
    NONPROJECT = "непроектный"


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        # self.clear_database()
        self.create_tables()

    def clear_database(self):
        with self.conn.cursor() as cursor:
            tables = [
                "worker",
                "project",
                "task",
                "project_worker",
                "project_task",
                "time_entry"
            ]

            for table in tables:
                cursor.execute(f"""
                    DROP TABLE IF EXISTS {table} CASCADE;
                """)
            self.conn.commit()

    def create_tables(self):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS worker (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    position VARCHAR(255)
                );

                CREATE TABLE IF NOT EXISTS project (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(20) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS project_worker (
                    project_id INTEGER REFERENCES project(id),
                    worker_id INTEGER REFERENCES worker(id),
                    PRIMARY KEY (project_id, worker_id)
                );

                CREATE TABLE IF NOT EXISTS project_task (
                    project_id INTEGER REFERENCES project(id),
                    task_id INTEGER REFERENCES task(id),
                    PRIMARY KEY (project_id, task_id)
                );

                CREATE TABLE IF NOT EXISTS time_entry (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES project(id),
                    worker_id INTEGER NOT NULL REFERENCES worker(id),
                    task_id INTEGER NOT NULL REFERENCES task(id),
                    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    hours DOUBLE PRECISION NOT NULL
                );
            """)
            self.conn.commit()

    # Worker methods
    def create_worker(self, name, position, telegram_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO worker (name, position, telegram_id) VALUES (%s, %s, %s) RETURNING id",
                (name, position, telegram_id)
            )
            worker_id = cursor.fetchone()[0]
            self.conn.commit()
            return worker_id

    def get_worker(self, worker_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM worker WHERE id = %s",
                (worker_id,)
            )
            return cursor.fetchone()

    # Project methods
    def create_project(self, name, project_type, task_ids, worker_ids):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO project (name, type) VALUES (%s, %s) RETURNING id",
                (name, project_type.value)
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

    def update_project(self, project_id, new_name=None, new_type=None, new_tasks=None, new_workers=None):
        with self.conn.cursor() as cursor:
            if new_name:
                cursor.execute(
                    "UPDATE project SET name = %s WHERE id = %s",
                    (new_name, project_id)
                )

            if new_type:
                cursor.execute(
                    "UPDATE project SET type = %s WHERE id = %s",
                    (new_type.value, project_id)
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
    def create_task(self, name):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO task (name) VALUES (%s) RETURNING id",
                (name,)
            )
            task_id = cursor.fetchone()[0]
            self.conn.commit()
            return task_id

    def get_task(self, task_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM task WHERE id = %s",
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
            cursor.execute(
                "SELECT * FROM worker"
            )
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