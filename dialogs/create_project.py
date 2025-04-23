from typing import Any, List, Dict
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel, Select
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery

from widgets.Vertical import Select, Multiselect


class CreateProjectState(StatesGroup):
    name = State()
    project_type = State()
    stage_selection = State()
    task_selection = State()
    custom_task_name = State()
    custom_task_department = State()
    custom_tasks = State()
    confirm = State()


async def project_confirm_getter(dialog_manager: DialogManager, **kwargs):
    base_data = await project_getter(dialog_manager, **kwargs)

    selected_tasks = dialog_manager.current_context().dialog_data.get("selected_tasks", [])
    tasks_list = "\n".join(
        [f"- {task['name']}" for task in selected_tasks]) if selected_tasks else "Нет выбранных задач"

    custom_tasks = dialog_manager.current_context().dialog_data.get("custom_tasks", [])
    custom_tasks_list = "\n".join(
        [f"- {task['name']} ({task['department'] or 'без отдела'})"
         for task in custom_tasks]) if custom_tasks else "Нет уникальных задач"

    return {
        **base_data,
        "tasks_list": tasks_list,
        "custom_tasks_list": custom_tasks_list
    }


async def project_getter(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.current_context().dialog_data
    db = dialog_manager.middleware_data["db"]

    project_type = data.get("project_type")
    stage = data.get("stage", None)
    selected_task_ids = data.get("selected_task_ids", [])

    tasks = db.get_tasks_by_stage(stage)
    tasks = [dict(task) for task in tasks]

    selected_tasks_info = []
    if selected_task_ids:
        selected_tasks_info = [dict(db.get_task(int(task_id))) for task_id in selected_task_ids]

    return {
        "name": data.get("name"),
        "project_type": "Не указан" if project_type is None else project_type,
        "stage": "Не указана" if stage is None else stage,
        "tasks": tasks,
        "selected_tasks": selected_tasks_info,
        "custom_tasks": data.get("custom_tasks", []),
    }


async def on_name_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Название проекта не может быть пустым. Пожалуйста, введите название.")
        return

    dialog_manager.current_context().dialog_data["name"] = message.text.strip()
    await dialog_manager.next()


async def on_project_type_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    dialog_manager.current_context().dialog_data["project_type"] = item_id
    await dialog_manager.next()


async def on_stage_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    stage = None if item_id == "NONE" else item_id
    dialog_manager.current_context().dialog_data["stage"] = stage
    await dialog_manager.next()


async def select_all_tasks(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data = await project_getter(dialog_manager)
    tasks = data.get("tasks", [])
    if not tasks:
        await callback.answer("Нет задач для выбора")
        return

    widget = dialog_manager.find("tasks_ms")
    for task in tasks:
        await widget.set_checked(str(task["id"]), True)

    await callback.answer("Все задачи выбраны")


async def on_back_from_tasks(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    widget = dialog_manager.find("tasks_ms")
    selected_task_ids = widget.get_checked()
    dialog_manager.current_context().dialog_data["selected_task_ids"] = [int(task_id) for task_id in selected_task_ids]
    dialog_manager.current_context().dialog_data["selected_tasks"] = [
        dict(dialog_manager.middleware_data["db"].get_task(int(task_id)))
        for task_id in selected_task_ids
    ]
    await dialog_manager.back()


async def on_custom_task_name_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Название задачи не может быть пустым. Пожалуйста, введите название.")
        return

    dialog_manager.current_context().dialog_data["current_custom_task"] = {
        "name": message.text.strip(),
        "department": None
    }
    await dialog_manager.switch_to(CreateProjectState.custom_task_department)


async def on_custom_task_department_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager,
                                             item_id):
    department = None if item_id == "None" else item_id
    current_task = dialog_manager.current_context().dialog_data["current_custom_task"]
    current_task["department"] = department

    custom_tasks = dialog_manager.current_context().dialog_data.setdefault("custom_tasks", [])
    custom_tasks.append(current_task.copy())

    await callback.answer(f"Добавлена задача: {current_task['name']} ({department or 'без отдела'})")
    await dialog_manager.switch_to(CreateProjectState.task_selection)


async def on_custom_tasks_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    text = message.text.strip()
    if not text:
        await message.answer("Пожалуйста, введите названия задач.")
        return

    task_names = [name.strip() for name in text.split(',') if name.strip()]
    custom_tasks = [{"name": name, "department": None} for name in task_names]

    dialog_manager.current_context().dialog_data.setdefault("custom_tasks", []).extend(custom_tasks)
    await dialog_manager.switch_to(CreateProjectState.confirm)


async def create_project(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    name = data.get("name")
    project_type = data.get("project_type")
    selected_task_ids = data.get("selected_task_ids", [])
    custom_tasks = data.get("custom_tasks", [])

    db = dialog_manager.middleware_data["db"]
    try:
        project_id = db.create_project(
            name=name,
            project_type=project_type,
            task_ids=selected_task_ids,
            worker_ids=[]
        )

        if custom_tasks:
            for task in custom_tasks:
                task_id = db.create_task(
                    name=task["name"],
                    stage=data.get("stage"),
                    department_type=task["department"],
                    is_unique=True
                )
                db.add_task_to_project(project_id, task_id)

            tasks_list = ", ".join(f"'{task['name']}'" for task in custom_tasks)
            await callback.answer(
                f"Проект '{name}' успешно создан (ID: {project_id}) с уникальными задачами: {tasks_list}"
            )
        else:
            await callback.answer(f"Проект '{name}' успешно создан (ID: {project_id})")

    except Exception as e:
        print(e)
        await callback.answer(f"Ошибка при создании проекта: {str(e)}")
    await dialog_manager.done()


def create_project_dialog():
    return Dialog(
        Window(
            Const("Введите название нового проекта:"),
            MessageInput(
                func=on_name_entered,
                content_types=["text"]
            ),
            Cancel(Const("❌ Отмена")),
            state=CreateProjectState.name,
        ),
        Window(
            Const("Выберите тип проекта:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("плановый", "Плановый"),
                    ("клиентский", "Клиентский"),
                    ("кастом", "Кастом"),
                    ("непроектный", "Непроектный"),
                ],
                id="project_type_select",
                item_id_getter=lambda x: x[0],
                on_click=on_project_type_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.project_type),
        Window(
            Const("Выберите стадию работы:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("подготовка", "Подготовка"),
                    ("отрисовка прямые", "Отрисовка прямые"),
                    ("отрисовка италики", "Отрисовка италики"),
                    ("отрисовка капитель", "Отрисовка капитель"),
                    ("техничка", "Техничка"),
                    ("оформление", "Оформление"),
                    ("NONE", "Задачи вне этапа")
                ],
                id="stage_select",
                item_id_getter=lambda x: x[0],
                on_click=on_stage_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Button(
                    Const("➡️ Подтвердить создание проекта"),
                    id="skip_tasks",
                    on_click=lambda c, w, d: d.switch_to(CreateProjectState.custom_tasks)
                ),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.stage_selection,
            getter=project_getter,
        ),
        Window(
            Const("Выберите задачи для добавления в проект:"),
            Multiselect(
                checked_text=Format("✅ {item[name]}"),
                unchecked_text=Format("❌ {item[name]}"),
                items="tasks",
                item_id_getter=lambda item: str(item["id"]),
                id="tasks_ms",
            ),
            Row(
                Button(
                    Const("⬅️ Назад"),
                    id="back_with_save",
                    on_click=on_back_from_tasks
                ),
                Button(
                    Const("✅ Выбрать все"),
                    id="select_all",
                    on_click=select_all_tasks
                ),
                Button(
                    Const("➕ Добавить кастомную задачу"),
                    id="add_custom_task",
                    on_click=lambda c, w, d: d.switch_to(CreateProjectState.custom_task_name)
                ),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.task_selection,
            getter=project_getter,
        ),
        Window(
            Const("Введите название кастомной задачи:"),
            MessageInput(
                func=on_custom_task_name_entered,
                content_types=["text"]
            ),
            Row(
                Back(Const("⬅️ Назад к выбору задач")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.custom_task_name,
        ),
        Window(
            Const("Выберите отдел для кастомной задачи:"),
            Select(
                text=Format("{item[1]}"),
                items=[
                    ("шрифтовой", "Шрифтовой"),
                    ("технический", "Технический"),
                    ("графический", "Графический"),
                    ("None", "Без отдела"),
                ],
                id="custom_task_dept_select",
                item_id_getter=lambda x: x[0],
                on_click=on_custom_task_department_selected,
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.custom_task_department,
        ),
        Window(
            Format(
                "Подтвердите создание проекта:\n\n"
                "Название: {name}\n"
                "Тип проекта: {project_type}\n"
                "Стадия: {stage}\n\n"
                "Выбранные задачи:\n"
                "{tasks_list}\n\n"
                "Уникальные задачи проекта:\n"
                "{custom_tasks_list}"
            ),
            Button(
                Const("✅ Создать проект"),
                id="confirm",
                on_click=create_project
            ),
            Row(
                Button(
                    Const("⬅️ Назад к выбору стадии"),
                    id="back_stage_selection",
                    on_click=lambda c, w, d: d.switch_to(CreateProjectState.stage_selection)
                ),
                Cancel(Const("❌ Отмена"))
            ),
            state=CreateProjectState.confirm,
            getter=project_confirm_getter,
        ),
    )
