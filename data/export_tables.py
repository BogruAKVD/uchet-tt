import csv
import io
import zipfile
from typing import List, Dict
from psycopg2.extras import DictCursor
from data.database import Database


class TableExporter:
    @staticmethod
    def get_all_tables(db: Database) -> List[str]:
        with db.conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def export_table_to_csv(db: Database, table_name: str) -> str:
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            if not rows:
                return ""

            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow([desc[0] for desc in cursor.description])

            for row in rows:
                writer.writerow(row)

            return output.getvalue()

    @staticmethod
    def export_all_tables_to_zip(db: Database) -> io.BytesIO:
        tables = TableExporter.get_all_tables(db)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
            for table in tables:
                csv_data = TableExporter.export_table_to_csv(db, table)
                if csv_data:
                    zip_file.writestr(f"{table}.csv", csv_data)

        zip_buffer.seek(0)
        return zip_buffer