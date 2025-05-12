from database import db


def is_admin(user_id: int) -> bool:
    return db.is_admin(telegram_id=user_id)


def is_worker(user_id: int) -> bool:
    return db.get_worker_by_telegram_id(telegram_id=user_id) is not None
