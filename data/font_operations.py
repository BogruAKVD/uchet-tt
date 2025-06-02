from psycopg2.extras import DictCursor
from data.database import Database

class FontOperations:
    @staticmethod
    def get_fonts(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT id, name FROM font ORDER BY name")
            return cursor.fetchall()

    @staticmethod
    def get_font_name(db: Database, font_id: int) -> str:
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT name FROM font WHERE id = %s
                """, (font_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
            except Exception as e:
                print(f"Ошибка при получении названия шрифта: {e}")
                return ""
