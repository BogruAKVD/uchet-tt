import os
# from bot import db

ADMIN_ID = int(os.getenv("ADMIN_ID"))


def is_admin(user_id: int) -> bool:
    # return user_id == ADMIN_ID
    return True


# def is_worker(user_id: int) -> bool:
#     return db.get_worker_by_telegram_id(telegram_id=user_id) is not None

