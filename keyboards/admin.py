from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestUser
from database import ProjectType

def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Добавить проект"),
                KeyboardButton(text="Редактировать проект"),
            ],
            [
                KeyboardButton(text="Добавить тип задачи"),
                KeyboardButton(text="Добавить сотрудника"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def project_type_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=ProjectType.CLIENT.value, callback_data="project_type:client"),
                InlineKeyboardButton(text=ProjectType.PROJECT.value, callback_data="project_type:project"),
                InlineKeyboardButton(text=ProjectType.NONPROJECT.value, callback_data="project_type:nonproject"),
            ]
        ]
    )
    return keyboard

def confirm_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm"),
            ]
        ]
    )
    return keyboard

def create_task_keyboard(tasks, selected_tasks=None):
    buttons = []
    if selected_tasks is None:
        selected_tasks = {}
    for task in tasks:
        selected = selected_tasks.get(task['id'], False)
        button_text = f"{task['name']} {'✅' if selected else '❌'}"
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"task:{task['id']}:{1 if selected else 0}"
        )
        buttons.append([button])
    buttons.append([InlineKeyboardButton(text="Подтвердить выбор задач", callback_data="tasks:confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def create_worker_keyboard(workers, selected_workers=None):
    buttons = []
    if selected_workers is None:
        selected_workers = {}
    for worker in workers:
        selected = selected_workers.get(worker['id'], False)
        button_text = f"{worker['name']} {'✅' if selected else '❌'}"
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"worker:{worker['id']}:{1 if selected else 0}"
        )
        buttons.append([button])
    buttons.append([InlineKeyboardButton(text="Подтвердить выбор сотрудников", callback_data="workers:confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def create_project_keyboard(projects):
    buttons = []
    for project in projects:
        button = InlineKeyboardButton(
            text=project['name'],
            callback_data=f"project:{project['id']}"
        )
        buttons.append([button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def create_edit_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить название", callback_data="edit:name"),
                InlineKeyboardButton(text="Изменить тип", callback_data="edit:type"),
            ],
            [
                InlineKeyboardButton(text="Изменить задачи", callback_data="edit:tasks"),
                InlineKeyboardButton(text="Изменить сотрудников", callback_data="edit:workers"),
            ]
        ]
    )
    return keyboard

def get_worker_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Запросить ID сотрудника", request_user=KeyboardButtonRequestUser(request_id=1))
            ]
        ],
        resize_keyboard=True
    )
    return keyboard
