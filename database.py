import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import DictCursor
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# Database credentials
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DB = os.getenv("DB_DB")


class ProjectType(Enum):
    PLANNED = "плановый"
    CLIENT = "клиентский"
    FOR_CUSTOM = "для кастома"
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


class WeekDay(Enum):
    MONDAY = "понедельник"
    TUESDAY = "вторник"
    WEDNESDAY = "среда"
    THURSDAY = "четверг"
    FRIDAY = "пятница"
    SATURDAY = "суббота"
    SUNDAY = "воскресенье"


class TaskStatus(Enum):
    IN_PROGRESS = "в процессе"
    COMPLETED = "готова"


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DB,
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
                self.create_worker_active_project_table(cursor)
                self.create_time_entry_table(cursor)
                self.create_admin_table(cursor)
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
                reminder_day TEXT CHECK (reminder_day IN ('понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье')) DEFAULT 'пятница',
                reminder_time TIME WITHOUT TIME ZONE DEFAULT '17:00:00',
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
                type TEXT NOT NULL CHECK (type IN ('плановый', 'клиентский', 'для кастома', 'непроектный')),
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
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES project(id),
                task_id INTEGER REFERENCES task(id),
                font_id INTEGER REFERENCES font(id),
                status VARCHAR(20) NOT NULL DEFAULT 'в процессе',
                comments TEXT
            );
        """)

    def create_time_entry_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entry (
                id SERIAL PRIMARY KEY,
                project_task_id INTEGER NOT NULL REFERENCES project_task(id),
                worker_id INTEGER NOT NULL REFERENCES worker(id),
                entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
                hours DOUBLE PRECISION NOT NULL CHECK (hours > 0)
            );
        """)

    def create_worker_active_project_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_active_project (
                worker_id INTEGER NOT NULL REFERENCES worker(id),
                project_id INTEGER NOT NULL REFERENCES project(id),
                PRIMARY KEY (worker_id, project_id)
            );
        """)

    def create_admin_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

    # Worker methods
    def create_worker(self, name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks=False,
                      can_receive_non_project_tasks=False, reminder_day="пятница", reminder_time="17:00:00"):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO worker 
                (name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks, 
                 can_receive_non_project_tasks, reminder_day, reminder_time) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (name, telegram_id, position_id, weekly_hours, can_receive_custom_tasks,
                 can_receive_non_project_tasks, reminder_day, reminder_time)
            )
            worker_id = cursor.fetchone()[0]
            self.conn.commit()
            return worker_id

    def get_worker(self, worker_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
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

    def update_worker(self, worker_id, name=None, position_id=None, weekly_hours=None, can_receive_custom_tasks=None,
                      can_receive_non_project_tasks=None, reminder_day=None, reminder_time=None):
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

    def get_all_positions(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM position")
            return cursor.fetchall()

    # Project methods
    def create_project(self, name: str, project_type: str, tasks_with_fonts: List[dict] = None,
                       custom_tasks_with_fonts: List[dict] = None,
                       status: str = Status.IN_PROGRESS.value) -> int:
        """Создает новый проект с возможностью привязки задач к шрифтам по имени шрифта.

        Args:
            name: Название проекта
            project_type: Тип проекта (из ProjectType)
            tasks_with_fonts: Список словарей вида [{
                'task_id': int,
                'font_name': Optional[str],
                'comments': Optional[str]
            }]
            custom_tasks_with_fonts: Список словарей вида [{
                'name': str,
                'stage': Optional[str],
                'department': Optional[str],
                'font_name': Optional[str],
                'comments': Optional[str]
            }]
            status: Статус проекта (из Status)

        Returns:
            ID созданного проекта
        """
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO project (name, type, status) VALUES (%s, %s, %s) RETURNING id",
                    (name, project_type, status))
                project_id = cursor.fetchone()[0]

                font_names = set()

                if tasks_with_fonts:
                    font_names.update(task['font_name'] for task in tasks_with_fonts
                                      if task.get('font_name') is not None)

                if custom_tasks_with_fonts:
                    font_names.update(task['font_name'] for task in custom_tasks_with_fonts
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

                if custom_tasks_with_fonts:
                    for custom_task in custom_tasks_with_fonts:
                        task_id = self.create_task(
                            name=custom_task['name'],
                            stage=custom_task.get('stage'),
                            department_type=custom_task.get('department'),
                            is_unique=True
                        )

                        font_id = None
                        if custom_task.get('font_name') is not None:
                            font_id = font_name_to_id.get(custom_task['font_name'])

                        cursor.execute(
                            """INSERT INTO project_task 
                            (project_id, task_id, font_id, comments) 
                            VALUES (%s, %s, %s, %s)""",
                            (project_id,
                             task_id,
                             font_id,
                             custom_task.get('comments'))
                        )

                self.conn.commit()
                return project_id
            except Exception as e:
                self.conn.rollback()
                raise Exception(f"Ошибка при создании проекта: {e}")

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

    def get_time_entries(self, worker_id, project_id=None, task_id=None, font_id=None, start_date: datetime = None,
                         end_date: datetime = None,
                         limit=None):
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:  # Add DictCursor here
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

    # Font methods

    def get_fonts(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT id, name FROM font ORDER BY name")
            return cursor.fetchall()

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
                JOIN project_task pt ON p.id = pt.project_id
                JOIN time_entry te ON pt.id = te.project_task_id
                WHERE te.worker_id = %s
                ORDER BY p.name
            """, (worker_id,))
            return cursor.fetchall()

    def get_task_by_id(self, task_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM task WHERE id = %s",
                (task_id,)
            )
            result = dict(cursor.fetchone())
            print(result)
            return result

    def get_all_workers(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
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
        if worker:
            return dict(worker)
        return None

    def get_tasks_by_stage(self, stage: str):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            stage = None if stage == "None" else stage

            cursor.execute("""
                SELECT t.id, t.name, t.stage, t.department_type
                FROM task t
                WHERE t.stage IS NOT DISTINCT FROM %s
                ORDER BY t.name
            """, (stage,))
            return [dict(row) for row in cursor.fetchall()]

    def get_project_task_info(self, project_task_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
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

    def get_tasks_for_project(self, project_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:  # Note DictCursor here
            cursor.execute("""
                SELECT pt.id, t.name, f.name as font_name
                FROM project_task pt
                JOIN task t ON pt.task_id = t.id
                LEFT JOIN font f ON pt.font_id = f.id
                WHERE pt.project_id = %s;
            """, (project_id,))
            return cursor.fetchall()

    def get_worker_active_projects_full(self, worker_id: int) -> list[dict]:
        with self.conn.cursor() as cursor:
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

    def get_worker_active_projects(self, worker_id: int) -> List[int]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT project_id FROM worker_active_project WHERE worker_id = %s",
                (worker_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def set_worker_active_projects(self, worker_id: int, project_ids: List[int]):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM worker_active_project WHERE worker_id = %s",
                (worker_id,)
            )
            for project_id in project_ids:
                cursor.execute(
                    "INSERT INTO worker_active_project (worker_id, project_id) VALUES (%s, %s)",
                    (worker_id, project_id)
                )
            self.conn.commit()

    def update_worker_reminder_settings(self, worker_id: int, day: str, time: str):
        """Update worker's reminder day and time

        Args:
            worker_id: ID of worker
            day: Day of week in Russian (e.g. "пятница")
            time: Time in format "HH:MM" or "HH:MM:SS"
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "UPDATE worker SET reminder_day = %s, reminder_time = %s WHERE id = %s",
                (day, time, worker_id)
            )
            self.conn.commit()

    def get_available_projects(self, worker_id: int) -> List[Dict[str, Any]]:
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT p.id, p.name 
                FROM project p
                WHERE p.status = 'в работе' AND p.type != 'для кастома'
                ORDER BY p.name
            """, (worker_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_project_name(self, project_id: int) -> str:
        """Получает название проекта по ID.

        Args:
            project_id: ID проекта

        Returns:
            Название проекта или пустая строка если не найден
        """
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT name FROM project WHERE id = %s
                """, (project_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
            except Exception as e:
                print(f"Ошибка при получении названия проекта: {e}")
                return ""

    def get_task_name(self, task_id: int) -> str:
        """Получает название задачи по ID.

        Args:
            task_id: ID задачи

        Returns:
            Название задачи или пустая строка если не найдена
        """
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT name FROM task WHERE id = %s
                """, (task_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
            except Exception as e:
                print(f"Ошибка при получении названия задачи: {e}")
                return ""

    def get_font_name(self, font_id: int) -> str:
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT name FROM font WHERE id = %s
                """, (font_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
            except Exception as e:
                print(f"Ошибка при получении названия шрифта: {e}")
                return ""

    def add_time_entry(self, time_entry_data):
        """Добавляет запись о затраченном времени.

        Args:
            time_entry_data: Словарь с данными {
                "project_task_id": int,
                "worker_id": int,
                "hours": float
            }

        Returns:
            True если запись успешно добавлена, False в случае ошибки
        """
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO time_entry (project_task_id, worker_id, hours)
                VALUES (%(project_task_id)s, %(worker_id)s, %(hours)s);
            """, time_entry_data)
            self.conn.commit()

    def get_time_entry(self, entry_id):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
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

    def update_time_entry(self, entry_id, hours):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """
                    UPDATE time_entry
                    SET hours = %s
                    WHERE id = %s
                    """,
                    (hours, entry_id)
                )
                self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении записи времени: {e}")
            return False

    def delete_time_entry(self, entry_id):
        """
        Delete a time entry

        Args:
            entry_id: ID of the entry to delete
        """
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM time_entry WHERE id = %s", (entry_id,))
            self.conn.commit()
            return cursor.rowcount > 0

    def is_admin(self, telegram_id: int) -> bool:
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT 1 FROM admin WHERE telegram_id = %s
                """, (telegram_id,))
                return cursor.fetchone() is not None
            except Exception as e:
                print(f"Ошибка при проверке администратора: {e}")
                return False

    def get_custom_project(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                 SELECT id, name FROM project 
                 WHERE type = 'для кастома' 
                 LIMIT 1;
             """)
            return dict(cursor.fetchone())

    def add_custom_task(self, task_name, font_id, custom_project_id=None):
        """
        Добавляет кастомную задачу в систему.

        Args:
            task_name (str): Название кастомной задачи
            font_id (int): ID шрифта, связанного с задачей
            custom_project_id (int, optional): ID проекта для кастомных задач.
                Если не указан, будет найден первый проект типа 'кастом'.

        Returns:
            int: ID созданной project_task или None в случае ошибки
        """
        with self.conn.cursor() as cursor:
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

                # Создаем уникальную задачу
                cursor.execute("""
                    INSERT INTO task (name, is_unique)
                    VALUES (%s, TRUE)
                    RETURNING id;
                """, (task_name,))
                task_id = cursor.fetchone()[0]

                # Создаем связь задачи с проектом
                cursor.execute("""
                    INSERT INTO project_task (project_id, task_id, font_id)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (custom_project_id, task_id, font_id))
                project_task_id = cursor.fetchone()[0]

                self.conn.commit()
                return project_task_id

            except Exception as e:
                self.conn.rollback()
                print(f"Ошибка при добавлении кастомной задачи: {e}")
                return None


db = Database()
# db.drop_all_tables()
db.create_tables()
