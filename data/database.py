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
                self.create_time_entry_detail_view(cursor)
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
                can_receive_nonproject_tasks BOOLEAN DEFAULT FALSE
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
                department TEXT NOT NULL CHECK (department IN ('шрифтовой', 'технический', 'графический', 'контентный')),
                UNIQUE (name, department)
            );
        """)

    def create_project_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('плановый', 'клиентский', 'для кастомов', 'для непроектных')),
                status TEXT NOT NULL DEFAULT 'в работе' CHECK (status IN ('в работе', 'завершён', 'на паузе', 'отменен'))
            );
        """)

        # Таблица для хранения истории изменений статуса проекта
        cursor.execute("""
               CREATE TABLE IF NOT EXISTS project_status_history (
                   id SERIAL PRIMARY KEY,
                   project_id INTEGER NOT NULL REFERENCES project(id),
                   old_status TEXT NOT NULL,
                   changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
               );
           """)

        # Триггерная функция для логирования изменений статуса
        cursor.execute("""
               CREATE OR REPLACE FUNCTION log_project_status_change()
               RETURNS TRIGGER AS $$
               BEGIN
                   IF NEW.status <> OLD.status THEN
                       INSERT INTO project_status_history (project_id, old_status)
                       VALUES (OLD.id, OLD.status);
                   END IF;
                   RETURN NEW;
               END;
               $$ LANGUAGE plpgsql;
           """)

        # Создание триггера
        cursor.execute("""
               DROP TRIGGER IF EXISTS project_status_change_trigger ON project;
               CREATE TRIGGER project_status_change_trigger
               AFTER UPDATE OF status ON project
               FOR EACH ROW
               EXECUTE FUNCTION log_project_status_change();
           """)

        #Проекты для непроектных и кастомных задач
        cursor.execute("""
            INSERT INTO project (name, type, status)
            SELECT 'Для кастомных задач', 'для кастомов', 'в работе'
            WHERE NOT EXISTS (
                SELECT 1 FROM project WHERE type = 'для кастомов'
            );
        """)

        cursor.execute("""
            INSERT INTO project (name, type, status)
            SELECT 'Для непроектных задач', 'для непроектных', 'в работе'
            WHERE NOT EXISTS (
                SELECT 1 FROM project WHERE type = 'для непроектных'
            );
        """)


    def create_task_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                stage TEXT NULL,
                department TEXT NULL,
                is_unique BOOLEAN NOT NULL DEFAULT FALSE,
                is_nonproject BOOLEAN NOT NULL DEFAULT FALSE,
                is_custom BOOLEAN NOT NULL DEFAULT FALSE
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
                hours DOUBLE PRECISION NOT NULL CHECK (hours > 0),
                comment TEXT
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

    def create_time_entry_detail_view(self, cursor):
        cursor.execute("""
            CREATE OR REPLACE VIEW time_entry_detail AS
            SELECT 
                te.id,
                te.entry_date,
                te.hours,
                te.comment,

                -- Worker details
                w.id AS worker_id,
                w.telegram_id AS worker_telegram_id,
                w.name AS worker_name,
                w.weekly_hours,
                w.reminder_day,
                w.reminder_time,
                w.can_receive_custom_tasks,
                w.can_receive_nonproject_tasks,

                -- Position details
                p.id AS position_id,
                p.name AS position_name,
                p.department AS position_department,

                -- Project details
                prj.id AS project_id,
                prj.name AS project_name,
                prj.type AS project_type,
                prj.status AS project_status,

                -- Task details
                t.id AS task_id,
                t.name AS task_name,
                t.stage AS task_stage,
                t.department AS task_department,
                t.is_unique AS task_is_unique,
                t.is_custom AS task_is_custom,
                t.is_nonproject AS task_is_nonproject,


                -- Font details
                f.id AS font_id,
                f.name AS font_name,

                -- Project task details
                pt.id AS project_task_id,
                pt.status AS project_task_status,
                pt.comments AS project_task_comments

            FROM time_entry te
            JOIN worker w ON te.worker_id = w.id
            LEFT JOIN position p ON w.position_id = p.id
            JOIN project_task pt ON te.project_task_id = pt.id
            JOIN project prj ON pt.project_id = prj.id
            JOIN task t ON pt.task_id = t.id
            LEFT JOIN font f ON pt.font_id = f.id;
        """)


db = Database()

# Инициализация таблиц
# db.drop_all_tables()
db.create_tables()

