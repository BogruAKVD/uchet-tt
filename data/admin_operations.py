from data.database import Database


class AdminOperations:
    def is_admin(db: Database, telegram_id: int) -> bool:
        with db.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT 1 FROM admin WHERE telegram_id = %s
                """, (telegram_id,))
                return cursor.fetchone() is not None
            except Exception as e:
                print(f"Ошибка при проверке администратора: {e}")
                return False
