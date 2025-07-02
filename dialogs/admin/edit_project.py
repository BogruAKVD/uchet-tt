from typing import Any, Dict
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram.types import CallbackQuery, Message
from aiogram_dialog.widgets.input import MessageInput

from data.models import Status
from data.project_operations import ProjectOperations
from data.task_operations import TaskOperations
from widgets.Vertical import Select, Radio
from widgets.Vertical import Multiselect


class EditProjectState(StatesGroup):
    select_project = State()
    project_actions = State()
    select_stage = State()
    select_task = State()
    change_status = State()
    font_selection = State()
    new_font = State()
    task_stage_selection = State()
    task_selection = State()
    unique_task_department = State()
    unique_task_name = State()


# Геттеры данных
async def get_projects(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    projects = ProjectOperations.get_all_projects(db)
    return {
        "projects": [(str(p["id"]), p["name"]) for p in projects]
    }


async def get_project_info(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    project_id = dialog_manager.current_context().dialog_data["project_id"]
    project = ProjectOperations.get_project_by_id(db, project_id)
    return {
        "project_name": project["name"],
        "project_type": project["type"],
        "current_status": project["status"]
    }


async def get_project_stages(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    project_id = dialog_manager.current_context().dialog_data["project_id"]
    stages = ProjectOperations.get_project_stages(db, project_id)

    stage_items = [(stage, stage) for stage in stages if stage is not None]
    stage_items.append(("None", "Без этапа"))

    return {
        "stage_items": stage_items,
        **await get_project_info(dialog_manager)
    }


async def get_stage_tasks(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    project_id = dialog_manager.current_context().dialog_data["project_id"]
    stage = dialog_manager.current_context().dialog_data.get("stage")

    tasks = ProjectOperations.get_project_tasks_by_stage(db, project_id, stage)

    formatted_tasks = []
    for task in tasks:
        status_emoji = "✅" if task['status'] == 'завершён' else "🔄"
        formatted_tasks.append({
            **task,
            'display_name': f"{status_emoji} {task['name']}"
        })

    return {
        "tasks": formatted_tasks,
        "stage": stage or "Без этапа",
        **await get_project_info(dialog_manager)
    }

async def get_font_selection_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    dialog_data = dialog_manager.current_context().dialog_data
    return {
        "fonts": dialog_data.get("fonts", ["Без шрифта"]),
        **await get_project_info(dialog_manager)
    }


async def get_status_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    project_id = dialog_manager.current_context().dialog_data["project_id"]
    project = ProjectOperations.get_project_by_id(db, project_id)

    statuses = []
    for status in Status:
        is_current = status.value == project["status"]
        statuses.append((
            status.value,
            f"{get_status_emoji(status)} {status.value}",
            is_current
        ))

    return {
        "statuses": statuses,
        "current_status": project["status"],
        **await get_project_info(dialog_manager)
    }

async def get_task_stages(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    return {
        "stages": [
            ("подготовка", "Подготовка"),
            ("отрисовка прямые", "Отрисовка прямые"),
            ("отрисовка италики", "Отрисовка италики"),
            ("отрисовка капитель", "Отрисовка капитель"),
            ("техничка", "Техничка"),
            ("оформление", "Оформление"),
            (None, "Без этапа")
        ],
        **await get_project_info(dialog_manager)
    }

async def get_add_tasks_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    db = dialog_manager.middleware_data["db"]
    data = dialog_manager.current_context().dialog_data

    current_font_name = data.get("current_font_name", "Без шрифта")
    stage = data.get("task_stage", None)

    tasks = []
    if stage:
        tasks = TaskOperations.get_tasks_by_stage(db, stage)
        for task in tasks:
            task['font_name'] = current_font_name

    return {
        "current_font_name": current_font_name,
        "task_stage": "Не указана" if stage is None else stage,
        "tasks": tasks,
        "unique_tasks": data.get("unique_tasks", []),
        **await get_project_info(dialog_manager)
    }


def get_status_emoji(status: Status) -> str:
    emoji_map = {
        Status.IN_PROGRESS: "🔄",
        Status.COMPLETED: "✅",
        Status.ON_HOLD: "⏸️",
        Status.CANCELLED: "❌"
    }
    return emoji_map.get(status, "🔘")


async def on_task_selected(c: CallbackQuery, widget: Multiselect, manager: DialogManager, item_id: str):
    await save_added_tasks(c, widget, manager)
    await manager.show()


async def on_unique_task_name_entered(message: Message, widget: MessageInput, manager: DialogManager):
    data = manager.current_context().dialog_data
    current_font_name = data.get("current_font_name")
    department = data["current_unique_task"]["department"]
    stage = data.get("stage")

    task_names = [name.strip() for name in message.text.split('\n') if name.strip()]

    if not task_names:
        await message.answer("Название задачи не может быть пустым. Пожалуйста, введите название.")
        return

    unique_tasks = data.setdefault("unique_tasks", [])

    for task_name in task_names:
        unique_task = {
            "name": task_name,
            "stage": stage,
            "department": department,
            "font_name": current_font_name,
            "comments": None
        }
        unique_tasks.append(unique_task)

    db = manager.middleware_data["db"]
    project_id = data["project_id"]

    with db.conn.cursor() as cursor:
        try:
            font_id = None
            if current_font_name and current_font_name != "Без шрифта":
                cursor.execute(
                    "SELECT id FROM font WHERE name = %s",
                    (current_font_name,))
                font_row = cursor.fetchone()

                if font_row:
                    font_id = font_row[0]
                else:
                    cursor.execute(
                        "INSERT INTO font (name) VALUES (%s) RETURNING id",
                        (current_font_name,))
                    font_id = cursor.fetchone()[0]

            for unique_task in unique_tasks:
                task_id = TaskOperations.create_task(
                    db,
                    name=unique_task['name'],
                    stage=unique_task.get('stage'),
                    department=unique_task.get('department'),
                    is_unique=True
                )

                cursor.execute(
                    """INSERT INTO project_task 
                    (project_id, task_id, font_id, comments) 
                    VALUES (%s, %s, %s, %s)""",
                    (project_id,
                     task_id,
                     font_id,
                     unique_task.get('comments'))
                )

            db.conn.commit()
            await message.answer(f"Добавлены {len(task_names)} задачи в отдел {department or 'без отдела'}")
            await manager.switch_to(EditProjectState.project_actions)
        except Exception as e:
            db.conn.rollback()
            await message.answer(f"Ошибка при добавлении задач: {str(e)}", show_alert=True)

async def on_project_selected(c: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    manager.current_context().dialog_data["project_id"] = int(item_id)
    await manager.next()


async def on_stage_selected(c: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    manager.current_context().dialog_data["stage"] = None if item_id == "None" else item_id
    await manager.next()


async def toggle_task_status(c: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    db = manager.middleware_data["db"]
    new_status = 'в процессе' if ProjectOperations.get_project_task(db, item_id)['status'] == 'завершён' else 'завершён'
    ProjectOperations.update_task_status(db, item_id, new_status)
    await c.answer(f"Статус изменён на: {new_status}")
    await manager.show()


async def toggle_stage_status(c: CallbackQuery, button: Button, manager: DialogManager):
    db = manager.middleware_data["db"]
    project_id = manager.current_context().dialog_data["project_id"]
    stage = manager.current_context().dialog_data.get("stage")

    tasks = ProjectOperations.get_project_tasks_by_stage(db, project_id, stage)
    all_completed = all(t['status'] == 'завершён' for t in tasks)
    new_status = 'в процессе' if all_completed else 'завершён'

    if new_status == 'завершён':
        ProjectOperations.complete_stage_tasks(db, project_id, stage)
    else:
        ProjectOperations.incomplete_stage_tasks(db, project_id, stage)

    await c.answer(f"Все задачи этапа {'завершены' if new_status == 'завершён' else 'возобновлены'}")
    await manager.show()


async def on_status_selected(c: CallbackQuery, radio: Radio, manager: DialogManager, item_id: str):
    db = manager.middleware_data["db"]
    project_id = manager.current_context().dialog_data["project_id"]
    ProjectOperations.update_project_status(db, project_id, item_id)
    await c.answer(f"Статус проекта изменён на: {item_id}")
    await manager.show()


async def on_add_tasks_click(c: CallbackQuery, button: Button, manager: DialogManager):
    dialog_data = manager.current_context().dialog_data
    dialog_data["fonts"] = ["Без шрифта"]
    dialog_data["current_font_name"] = "Без шрифта"
    dialog_data["unique_tasks"] = []
    await manager.switch_to(EditProjectState.font_selection)


async def on_font_selected(c: CallbackQuery, select: Select, manager: DialogManager, font_name: str):
    manager.current_context().dialog_data["current_font_name"] = font_name
    await manager.switch_to(EditProjectState.task_stage_selection)


async def on_new_font_entered(message: Message, widget: MessageInput, manager: DialogManager):
    font_name = message.text.strip()

    if not font_name:
        await message.answer("Название шрифта не может быть пустым. Пожалуйста, введите название.")
        return

    dialog_data = manager.current_context().dialog_data
    if "fonts" not in dialog_data:
        dialog_data["fonts"] = ["Без шрифта"]

    dialog_data["fonts"].append(font_name)
    dialog_data["current_font_name"] = font_name
    await manager.switch_to(EditProjectState.task_selection)

async def on_task_stage_selected(c: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    print(item_id)
    manager.current_context().dialog_data["task_stage"] = item_id
    await manager.switch_to(EditProjectState.task_selection)


async def select_all_tasks(c: CallbackQuery, button: Button, manager: DialogManager):
    data = await get_add_tasks_data(manager)
    tasks = data.get("tasks", [])
    if not tasks:
        await c.answer("Нет задач для выбора")
        return

    widget = manager.find("tasks_ms")
    current_font_name = data.get("current_font_name")

    for task in tasks:
        task_id = f"{task['id']}_{current_font_name}"
        await widget.set_checked(task_id, True)

    await c.answer("Все задачи выбраны")


async def on_unique_task_department_selected(c: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    manager.current_context().dialog_data["current_unique_task"] = {
        "department": item_id,
        "names": []
    }
    await manager.switch_to(EditProjectState.unique_task_name)


async def save_added_tasks(c: CallbackQuery, button: Button, manager: DialogManager):
    db = manager.middleware_data["db"]
    data = manager.current_context().dialog_data
    project_id = data["project_id"]

    widget = manager.find("tasks_ms")
    selected_task_ids_with_fonts = widget.get_checked() if widget else []

    tasks_with_fonts = []
    for task_id_with_font in selected_task_ids_with_fonts:
        parts = task_id_with_font.split('_')
        task_id = int(parts[0])
        font_name = parts[1] if parts[1] != "NONE" else None
        tasks_with_fonts.append({
            "task_id": task_id,
            "font_name": font_name,
            "comments": None
        })

    unique_tasks = data.get("unique_tasks", [])

    with db.conn.cursor() as cursor:
        try:
            # Добавляем шрифты, если они новые
            font_names = set()
            for task in tasks_with_fonts:
                if task.get('font_name'):
                    font_names.add(task['font_name'])

            for task in unique_tasks:
                if task.get('font_name'):
                    font_names.add(task['font_name'])

            font_name_to_id = {}
            for font_name in font_names:
                cursor.execute(
                    "SELECT id FROM font WHERE name = %s",
                    (font_name,))
                font_row = cursor.fetchone()

                if font_row:
                    font_id = font_row[0]
                else:
                    cursor.execute(
                        "INSERT INTO font (name) VALUES (%s) RETURNING id",
                        (font_name,))
                    font_id = cursor.fetchone()[0]

                font_name_to_id[font_name] = font_id

            if tasks_with_fonts:
                for task_info in tasks_with_fonts:
                    font_id = None
                    if task_info.get('font_name') is not None:
                        font_id = font_name_to_id.get(task_info['font_name'])

                    cursor.execute(
                        """INSERT INTO project_task 
                        (project_id, task_id, font_id, comments) 
                        VALUES (%s, %s, %s, %s)""",
                        (project_id,
                         task_info['task_id'],
                         font_id,
                         task_info.get('comments'))
                    )

            if unique_tasks:
                for unique_task in unique_tasks:
                    task_id = TaskOperations.create_task(
                        db,
                        name=unique_task['name'],
                        stage=unique_task.get('stage'),
                        department=unique_task.get('department'),
                        is_unique=True
                    )

                    font_id = None
                    if unique_task.get('font_name') is not None:
                        font_id = font_name_to_id.get(unique_task['font_name'])

                    cursor.execute(
                        """INSERT INTO project_task 
                        (project_id, task_id, font_id, comments) 
                        VALUES (%s, %s, %s, %s)""",
                        (project_id,
                         task_id,
                         font_id,
                         unique_task.get('comments'))
                    )

            db.conn.commit()
            await c.answer("Задача успешно добавлена в проект!")
            await manager.show()
        except Exception as e:
            db.conn.rollback()
            await c.answer(f"Ошибка при добавлении задач: {str(e)}", show_alert=True)


# Диалог
def edit_project_dialog() -> Dialog:
    return Dialog(
        Window(
            Const("Выберите проект для редактирования:"),
            Select(
                text=Format("{item[1]}"),
                items="projects",
                item_id_getter=lambda x: x[0],
                id="project_select",
                on_click=on_project_selected,
            ),
            Cancel(Const("❌ Отмена")),
            state=EditProjectState.select_project,
            getter=get_projects,
        ),
        Window(
            Format("Проект: <b>{project_name}</b>\n"
                   "Тип: <b>{project_type}</b>\n"
                   "Статус: <b>{current_status}</b>"),
            Button(
                Const("📋 Просмотреть задачи по этапам"),
                id="view_tasks",
                on_click=lambda c, w, m: m.switch_to(EditProjectState.select_stage)
            ),
            Button(
                Const("➕ Добавить задачи в проект"),
                id="add_tasks",
                on_click=on_add_tasks_click
            ),
            Button(
                Const("🔄 Изменить статус проекта"),
                id="change_status",
                on_click=lambda c, w, m: m.switch_to(EditProjectState.change_status)
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.project_actions,
            getter=get_project_info,
        ),
        Window(
            Const("Выберите этап:"),
            Select(
                text=Format("{item[1]}"),
                items="stage_items",
                item_id_getter=lambda x: x[0],
                id="stage_select",
                on_click=on_stage_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.select_stage,
            getter=get_project_stages,
        ),
        Window(
            Format("Этап: <b>{stage}</b>\nПроект: <b>{project_name}</b>"),
            Select(
                text=Format("{item[display_name]}"),
                items="tasks",
                item_id_getter=lambda x: x["id"],
                id="task_select",
                on_click=toggle_task_status,
            ),
            Button(
                Const("✅ Завершить/🔄 Возобновить весь этап"),
                id="toggle_stage",
                on_click=toggle_stage_status
            ),
            Row(
                Back(Const("⬅️ Назад к этапам")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.select_task,
            getter=get_stage_tasks,
        ),
        Window(
            Format("Изменение статуса проекта: <b>{project_name}</b>\nТекущий статус: <b>{current_status}</b>"),
            Radio(
                checked_text=Format("🔘 {item[1]}"),
                unchecked_text=Format("⚪ {item[1]}"),
                items="statuses",
                item_id_getter=lambda x: x[0],
                id="status_radio",
                on_click=on_status_selected,
            ),
            Row(
                Button(Const("⬅️ Назад"), id="back_to_project_actions",
                       on_click=lambda c, w, d: d.switch_to(EditProjectState.project_actions)),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.change_status,
            getter=get_status_data,
        ),
        Window(
            Const("Выберите шрифт для новых задач:"),
            Select(
                text=Format("{item}"),
                items="fonts",
                item_id_getter=lambda item: item,
                id="font_select",
                on_click=on_font_selected,
            ),
            Button(
                Const("➕ Добавить новый шрифт"),
                id="add_new_font",
                on_click=lambda c, w, d: d.switch_to(EditProjectState.new_font)
            ),
            Button(
                Const("🚫 Без шрифта"),
                id="no_font",
                on_click=lambda c, w, d: on_font_selected(c, w, d, "NONE")
            ),
            Row(
                Back(Const("⬅️ Назад к проекту")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.font_selection,
            getter=get_font_selection_data,
        ),
        Window(
            Const("Введите название нового шрифта:"),
            MessageInput(
                func=on_new_font_entered,
                content_types=["text"]
            ),
            Row(
                Back(Const("⬅️ Назад к выбору шрифта")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.new_font
        ),
        Window(
            Const("Выберите стадию для новых задач:"),
            Select(
                text=Format("{item[1]}"),
                items="stages",
                item_id_getter=lambda x: x[0],
                id="task_stage_select",
                on_click=on_task_stage_selected,
            ),
            Row(
                Back(Const("⬅️ Назад к выбору шрифта")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.task_stage_selection,
            getter=get_task_stages,
        ),
        Window(
            Format("Выберите задачи для добавления (шрифт: {current_font_name})"),
            Multiselect(
                checked_text=Format("✅ {item[name]}"),
                unchecked_text=Format("❌ {item[name]}"),
                items="tasks",
                item_id_getter=lambda item: f"{item['id']}_{item['font_name']}",
                id="tasks_ms",
                on_click=on_task_selected
            ),
            Row(
                Button(
                    Const("✅ Выбрать все"),
                    id="select_all",
                    on_click=select_all_tasks
                ),
                Button(
                    Const("➕ Добавить уникальную задачу"),
                    id="add_unique_task",
                    on_click=lambda c, w, d: d.switch_to(EditProjectState.unique_task_department)
                ),
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.task_selection,
            getter=get_add_tasks_data,
        ),
        Window(
            Const("Выберите отдел для уникальной задачи:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("шрифтовой", "Шрифтовой"),
                    ("технический", "Технический"),
                    ("графический", "Графический"),
                    ("контентный", "Контентный"),
                    ("None", "Без отдела"),
                ],
                id="unique_task_dept_select",
                item_id_getter=lambda x: x[0],
                on_click=on_unique_task_department_selected,
            ),
            Row(
                Back(Const("⬅️ Назад к выбору задач")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.unique_task_department,
        ),
        Window(
            Const("Введите названия уникальных задач (каждое название с новой строки):"),
            MessageInput(
                func=on_unique_task_name_entered,
                content_types=["text"]
            ),
            Row(
                Back(Const("⬅️ Назад к выбору отдела")),
                Cancel(Const("❌ Отмена")),
            ),
            state=EditProjectState.unique_task_name,
        )
    )
