import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DB"),
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


db = Database()

# Инициализация таблиц
# db.drop_all_tables()
db.create_tables()

