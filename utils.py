from data.admin_operations import AdminOperations
from data.database import db
from data.worker_operations import WorkerOperations


def is_admin(user_id: int) -> bool:
    return AdminOperations.is_admin(db, telegram_id=user_id)


def is_worker(user_id: int) -> bool:
    return WorkerOperations.get_worker_by_telegram_id(db, telegram_id=user_id) is not None
