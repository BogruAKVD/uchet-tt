from typing import Any, List, Dict, Optional
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Back, Cancel, Select
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery

from widgets.Vertical import Select as VerticalSelect, Multiselect


class CreateProjectState(StatesGroup):
    name = State()
    project_type = State()
    font_selection = State()
    new_font = State()
    stage_selection = State()
    task_selection = State()
    custom_task_name = State()
    custom_task_department = State()
    confirm = State()


async def project_confirm_getter(dialog_manager: DialogManager, **kwargs):
    base_data = await project_getter(dialog_manager, **kwargs)
    data = dialog_manager.current_context().dialog_data

    widget = dialog_manager.find("tasks_ms")
    selected_task_ids_with_fonts = widget.get_checked()

    return {
        "selected_task_ids_with_fonts": selected_task_ids_with_fonts,
        **base_data
    }


async def project_getter(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.current_context().dialog_data
    db = dialog_manager.middleware_data["db"]

    project_type = data.get("project_type")
    stage = data.get("stage", None)
    current_font_name = data.get("current_font_name")

    fonts = data.get("fonts", [])

    # Get tasks for current stage
    tasks = []
    if stage:
        tasks = db.get_tasks_by_stage(stage)
        tasks = [dict(task) for task in tasks]
        for task in tasks:
            task['font_name'] = current_font_name

    return {
        "name": data.get("name"),
        "project_type": "Не указан" if project_type is None else project_type,
        "current_font_name": current_font_name,
        "fonts": fonts,
        "stage": "Не указана" if stage is None else stage,
        "tasks": tasks,
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


async def on_new_font_entered(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    font_name = message.text.strip()

    if not font_name:
        await message.answer("Название шрифта не может быть пустым. Пожалуйста, введите название.")
        return

    dialog_manager.current_context().dialog_data.setdefault("fonts", []).append(font_name)
    dialog_manager.current_context().dialog_data["current_font_name"] = font_name
    await dialog_manager.switch_to(CreateProjectState.stage_selection)


async def on_font_selected(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, font_name):
    dialog_manager.current_context().dialog_data["current_font_name"] = font_name
    await dialog_manager.switch_to(CreateProjectState.stage_selection)


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
    current_font_name = data.get("current_font_name")

    for task in tasks:
        task_id = f"{task['id']}_{current_font_name}"
        await widget.set_checked(task_id, True)

    await callback.answer("Все задачи выбраны")


async def on_back_from_tasks(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
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
    current_task = {"name": dialog_manager.current_context().dialog_data["current_custom_task"],
                    "department": department}
    dialog_manager.current_context().dialog_data.setdefault("custom_tasks", []).append(current_task.copy())

    await callback.answer(f"Добавлена задача: {current_task['name']} ({department or 'без отдела'})")
    await dialog_manager.switch_to(CreateProjectState.task_selection)


async def create_project(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    name = data.get("name")
    project_type = data.get("project_type")
    custom_tasks = data.get("custom_tasks", [])
    fonts = data.get("fonts", [])
    db = dialog_manager.middleware_data["db"]

    widget = dialog_manager.find("tasks_ms")
    selected_task_ids_with_fonts = widget.get_checked()

    # Prepare tasks with fonts for project creation
    tasks_with_fonts = []
    for task_id_with_font in selected_task_ids_with_fonts:
        parts = task_id_with_font.split('_')
        task_id = int(parts[0])
        font_name = parts[1]
        tasks_with_fonts.append({
            "task_id": task_id,
            "font_name": font_name,
            "comments": None
        })
    try:
        # Create project with all tasks
        project_id = db.create_project(
            name=name,
            project_type=project_type,
            tasks_with_fonts=tasks_with_fonts,
        )
    except Exception as e:
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
            VerticalSelect(
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
            state=CreateProjectState.project_type
        ),
        Window(
            Format("Выберите шрифт для задач (текущий: {current_font_name})"),
            VerticalSelect(
                text=Format("{item[name]}"),
                items="fonts",
                item_id_getter=lambda item: str(item["id"]),
                id="font_select",
                on_click=on_font_selected,
            ),
            Button(
                Const("➕ Добавить новый шрифт"),
                id="add_new_font",
                on_click=lambda c, w, d: d.switch_to(CreateProjectState.new_font)
            ),
            Button(
                Const("🚫 Без шрифта"),
                id="no_font",
                on_click=lambda c, w, d: on_font_selected(c, w, d, "NONE")
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.font_selection,
            getter=project_getter
        ),
        Window(
            Const("Введите название нового шрифта:"),
            MessageInput(
                func=on_new_font_entered,
                content_types=["text"]
            ),
            Row(
                Back(Const("⬅️ Назад")),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.new_font
        ),
        Window(
            Const("Выберите стадию работы:"),
            VerticalSelect(
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
                    on_click=lambda c, w, d: d.switch_to(CreateProjectState.confirm)
                ),
                Cancel(Const("❌ Отмена")),
            ),
            state=CreateProjectState.stage_selection,
            getter=project_getter,
        ),
        Window(
            Format("Выберите задачи для добавления в проект (шрифт: {current_font_name})"),
            Multiselect(
                checked_text=Format("✅ {item[name]}"),
                unchecked_text=Format("❌ {item[name]}"),
                items="tasks",
                item_id_getter=lambda item: f"{item['id']}_{item['font_name']}",
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
            VerticalSelect(
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
                #TODO beter output
                "{selected_task_ids_with_fonts}\n\n"
                "Уникальные задачи проекта:\n"
                #TODO beter output
                "{custom_tasks}"
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
