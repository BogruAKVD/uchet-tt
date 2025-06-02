from psycopg2.extras import DictCursor
from data.database import Database


class PositionOperations:

    @staticmethod
    def create_position(db: Database, name, department):
        with db.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO position (name, department) VALUES (%s, %s) RETURNING id",
                (name, department)
            )
            position_id = cursor.fetchone()[0]
            db.conn.commit()
            return position_id

    @staticmethod
    def get_all_positions(db: Database):
        with db.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT * FROM position")
            return cursor.fetchall()
