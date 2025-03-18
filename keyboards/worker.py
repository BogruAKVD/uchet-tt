from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup


def worker_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Внести время"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def create_projects_keyboard(projects):
    buttons = []
    for project in projects:
        button = InlineKeyboardButton(
            text=project['name'],
            callback_data=f"project:{project['id']}"
        )
        buttons.append([button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def create_tasks_keyboard(tasks):
    buttons = []
    for task in tasks:
        button = InlineKeyboardButton(
            text=task['name'],
            callback_data=f"task:{task['id']}"
        )
        buttons.append([button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard