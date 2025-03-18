from aiogram.fsm.state import State, StatesGroup

# FSM States
class AddProject(StatesGroup):
    name = State()
    project_type = State()
    tasks = State()
    workers = State()
    confirm = State()

class EditProject(StatesGroup):
    project_select = State()
    action_select = State()
    new_name = State()
    new_type = State()
    new_tasks = State()
    new_workers = State()
    confirm = State()

class AddTaskType(StatesGroup):
    name = State()
    confirm = State()

class AddWorker(StatesGroup):
    name = State()
    position = State()
    telegram_id = State()
    confirm = State()

class AddTimeEntry(StatesGroup):
    choosing_project = State()
    choosing_task = State()
    entering_time = State()