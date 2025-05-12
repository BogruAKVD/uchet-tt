from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message, CallbackQuery

from widgets.Vertical import Multiselect, Select


class EditWorkerState(StatesGroup):
    select_worker = State()
    edit_options = State()
    edit_name = State()
    edit_position = State()
    edit_weekly_hours = State()
    edit_permissions = State()
    edit_projects = State()
    confirm = State()

async def workers_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    workers = db.get_all_workers()
    return {
        "workers": [dict(worker) for worker in workers]
    }

async def worker_edit_getter(dialog_manager: DialogManager, **kwargs):
    db = dialog_manager.middleware_data["db"]
    data = dialog_manager.current_context().dialog_data

    worker_id = data.get("worker_id")
    all_positions = db.get_all_positions()
    all_projects = db.get_all_projects()

    worker = None
    position_items = []
    current_position = None
    worker_projects = []
    project_items = []

    if worker_id:
        worker = db.get_worker(worker_id)
        worker_projects = db.get_worker_projects(worker_id)

        position_items = [(p['id'], p['name']) for p in all_positions]

        project_items = [(p['id'], p['name']) for p in all_projects]
        worker_project_ids = [p['id'] for p in worker_projects]

    default_perms = []
    if worker and worker.get('can_receive_custom_tasks', False):
        default_perms.append("custom_tasks")
    if worker and worker.get('can_receive_non_project_tasks', False):
        default_perms.append("non_project_tasks")
    print(default_perms)

    permissions = []
    if worker and worker.get('can_receive_custom_tasks', False):
        permissions.append("Кастомные задачи")
    if worker and worker.get('can_receive_non_project_tasks', False):
        permissions.append("Непроектные задачи")

    return {
        "worker": worker,
        "worker_name": worker['name'] if worker else "Не указано",
        "position_items": position_items,
        "current_position": current_position['name'] if current_position else "Не указана",
        "weekly_hours": worker['weekly_hours'] if worker and worker['weekly_hours'] else "Не указано",
        "permissions": permissions,
        "project_items": project_items,
        "worker_project_ids": worker_project_ids if worker_id else [],
        "worker_projects": [p['name'] for p in worker_projects],
        "default_perms": default_perms,
        "default_projects": [str(pid) for pid in worker_project_ids],
    }


async def confirm_getter(dialog_manager: DialogManager, **kwargs):
    worker_data = await worker_edit_getter(dialog_manager, **kwargs)
    data = dialog_manager.current_context().dialog_data

    position_items = worker_data.get("position_items", [])
    project_items = worker_data.get("project_items", [])

    # Получаем новые значения
    new_name = data.get("new_name")
    new_position_id = data.get("new_position_id")
    new_weekly_hours = data.get("new_weekly_hours")
    new_custom_tasks = data.get("new_can_receive_custom_tasks")
    new_non_project_tasks = data.get("new_can_receive_non_project_tasks")
    new_project_ids = data.get("new_project_ids", [])

    # Получаем текущие значения
    current_name = worker_data.get("worker", {}).get("name")
    current_position = worker_data.get("current_position")
    current_hours = worker_data.get("weekly_hours")
    current_permissions = worker_data.get("permissions", [])
    current_projects = worker_data.get("worker_projects", [])

    # Формируем строку изменений
    changes = []

    # Проверяем изменения для каждого поля
    if new_name is not None and new_name != current_name:
        changes.append(f"ФИО: {current_name} → {new_name}")

    if new_position_id is not None:
        new_position_name = next((p[1] for p in position_items if p[0] == new_position_id), None)
        if new_position_name != current_position:
            changes.append(f"Должность: {current_position} → {new_position_name}")

    if new_weekly_hours is not None and str(new_weekly_hours) != str(current_hours):
        changes.append(f"Часы в неделю: {current_hours} → {new_weekly_hours}")

    perm_changes = []
    if new_custom_tasks is not None:
        current_has_custom = "Кастомные задачи" in current_permissions
        if new_custom_tasks != current_has_custom:
            perm_changes.append("Кастомные задачи" if new_custom_tasks else "Нет кастомных задач")

    if new_non_project_tasks is not None:
        current_has_non_project = "Непроектные задачи" in current_permissions
        if new_non_project_tasks != current_has_non_project:
            perm_changes.append("Непроектные задачи" if new_non_project_tasks else "Нет непроектных задач")

    if perm_changes:
        changes.append(f"Разрешения: {', '.join(perm_changes)}")

    if new_project_ids:
        new_project_names = [p[1] for p in project_items if p[0] in new_project_ids]
        if set(new_project_names) != set(current_projects):
            added = set(new_project_names) - set(current_projects)
            removed = set(current_projects) - set(new_project_names)

            project_changes = []
            if added:
                project_changes.append(f"Добавлены: {', '.join(added)}")
            if removed:
                project_changes.append(f"Удалены: {', '.join(removed)}")

            if project_changes:
                changes.append("Проекты: " + "; ".join(project_changes))

    return {
        **worker_data,
        "new_name": new_name,
        "new_position_name": next(
            (p[1] for p in position_items if p[0] == new_position_id),
            None
        ) if new_position_id else None,
        "new_weekly_hours": new_weekly_hours,
        "new_permissions": [
            "Кастомные задачи" if new_custom_tasks else None,
            "Непроектные задачи" if new_non_project_tasks else None,
        ],
        "new_project_names": [
            p[1] for p in project_items
            if p[0] in new_project_ids
        ],
        "changes": "\n".join(changes) if changes else "Нет изменений",
    }

async def on_worker_selected(callback: CallbackQuery, select: Select,
                             dialog_manager: DialogManager, item_id: str):
    dialog_manager.current_context().dialog_data["worker_id"] = int(item_id)
    await dialog_manager.next()


async def on_name_entered(message: Message, widget: MessageInput,
                          dialog_manager: DialogManager):
    if not message.text.strip():
        await message.answer("Имя не может быть пустым. Пожалуйста, введите имя.")
        return

    dialog_manager.current_context().dialog_data["new_name"] = message.text.strip()
    await dialog_manager.switch_to(EditWorkerState.edit_options)


async def on_position_selected(callback: CallbackQuery, select: Select,
                               dialog_manager: DialogManager, item_id: str):
    dialog_manager.current_context().dialog_data["new_position_id"] = int(item_id)
    await dialog_manager.switch_to(EditWorkerState.edit_options)


async def on_hours_entered(message: Message, widget: MessageInput,
                           dialog_manager: DialogManager):
    try:
        hours = int(message.text.strip())
        if hours <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество часов (целое число больше 0).")
        return

    dialog_manager.current_context().dialog_data["new_weekly_hours"] = hours
    await dialog_manager.switch_to(EditWorkerState.edit_options)


async def on_permissions_updated(callback: CallbackQuery, button: Button,
                                 dialog_manager: DialogManager):
    widget = dialog_manager.find("perms_ms")
    selected_items = widget.get_checked()

    dialog_manager.current_context().dialog_data.update({
        "new_can_receive_custom_tasks": "custom_tasks" in selected_items,
        "new_can_receive_non_project_tasks": "non_project_tasks" in selected_items,
    })

    await dialog_manager.switch_to(EditWorkerState.edit_options)


async def on_projects_updated(callback: CallbackQuery, button: Button,
                              dialog_manager: DialogManager):
    widget = dialog_manager.find("projects_ms")
    selected_project_ids = [int(pid) for pid in widget.get_checked()]

    dialog_manager.current_context().dialog_data["new_project_ids"] = selected_project_ids
    await dialog_manager.switch_to(EditWorkerState.edit_options)


async def save_worker_changes(callback: CallbackQuery, button: Button,
                              dialog_manager: DialogManager):
    data = dialog_manager.current_context().dialog_data
    db = dialog_manager.middleware_data["db"]
    worker_id = data["worker_id"]

    try:
        db.update_worker(
            worker_id=worker_id,
            name=data.get("new_name"),
            position_id=data.get("new_position_id"),
            weekly_hours=data.get("new_weekly_hours"),
            can_receive_custom_tasks=data.get("new_can_receive_custom_tasks"),
            can_receive_non_project_tasks=data.get("new_can_receive_non_project_tasks")
        )

        if "new_project_ids" in data:
            current_projects = [p['id'] for p in db.get_worker_projects(worker_id)]
            new_projects = data["new_project_ids"]

            for project_id in current_projects:
                if project_id not in new_projects:
                    db.conn.cursor().execute(
                        "DELETE FROM project_worker WHERE worker_id = %s AND project_id = %s",
                        (worker_id, project_id)
                    )

            for project_id in new_projects:
                if project_id not in current_projects:
                    db.conn.cursor().execute(
                        "INSERT INTO project_worker (worker_id, project_id) VALUES (%s, %s)",
                        (worker_id, project_id)
                    )

            db.conn.commit()

        await callback.answer("Изменения сохранены успешно!")
    except Exception as e:
        await callback.answer(f"Ошибка при сохранении: {str(e)}")

    await dialog_manager.done()


async def go_to_edit_name(callback: CallbackQuery, button: Button,
                          dialog_manager: DialogManager):
    await dialog_manager.switch_to(EditWorkerState.edit_name)


async def go_to_edit_position(callback: CallbackQuery, button: Button,
                             dialog_manager: DialogManager):
    await dialog_manager.switch_to(EditWorkerState.edit_position)


async def go_to_edit_hours(callback: CallbackQuery, button: Button,
                           dialog_manager: DialogManager):
    await dialog_manager.switch_to(EditWorkerState.edit_weekly_hours)


async def go_to_edit_permissions(callback: CallbackQuery, button: Button,
                                 dialog_manager: DialogManager):
    await dialog_manager.switch_to(EditWorkerState.edit_permissions)


async def go_to_edit_projects(callback: CallbackQuery, button: Button,
                              dialog_manager: DialogManager):
    await dialog_manager.switch_to(EditWorkerState.edit_projects)


async def go_to_confirm(callback: CallbackQuery, button: Button,
                        dialog_manager: DialogManager):
    await dialog_manager.switch_to(EditWorkerState.confirm)


def edit_worker_dialog():
    return Dialog(
        Window(
            Const("Выберите сотрудника для редактирования:"),
            Select(
                text=Format("{item[name]} ({item[position_name]})"),
                items="workers",
                item_id_getter=lambda item: item["id"],
                id="worker_select",
                on_click=on_worker_selected,
            ),
            Cancel(Const("❌ Отмена")),
            state=EditWorkerState.select_worker,
            getter=workers_getter,
        ),
        Window(
            Format(
                "Редактирование сотрудника: {worker[name]}\n\n"
                "Текущие данные:\n"
                "Должность: {current_position}\n"
                "Часов в неделю: {weekly_hours}\n"
                "Разрешения: {permissions}\n"
                "Проекты: {worker_projects}\n\n"
                "Выберите что изменить:"
            ),
            Button(Const("Изменить ФИО"), id="edit_name", on_click=go_to_edit_name),
            Button(Const("Изменить должность"), id="edit_position", on_click=go_to_edit_position),
            Button(Const("Изменить рабочее время"), id="edit_weekly_hours", on_click=go_to_edit_hours),
            Button(Const("Изменить разрешения"), id="edit_permissions", on_click=go_to_edit_permissions),
            Button(Const("Изменить проекты"), id="edit_projects", on_click=go_to_edit_projects),
            Button(Const("✅ Сохранить изменения"), id="confirm", on_click=go_to_confirm),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Отмена")),
            state=EditWorkerState.edit_options,
            getter=worker_edit_getter,
        ),
        Window(
            Const("Введите новое имя сотрудника:"),
            MessageInput(
                func=on_name_entered,
                content_types=["text"]
            ),
            Back(Const("⬅️ Назад")),
            state=EditWorkerState.edit_name,
            getter=worker_edit_getter,
        ),
        Window(
            Const("Выберите новую должность:"),
            Select(
                text=Format("{item[1]}"),
                items="position_items",
                item_id_getter=lambda item: item[0],
                id="position_select",
                on_click=on_position_selected,
            ),
            Back(Const("⬅️ Назад")),
            state=EditWorkerState.edit_position,
            getter=worker_edit_getter,
        ),
        Window(
            Const("Введите новое количество рабочих часов в неделю:"),
            MessageInput(
                func=on_hours_entered,
                content_types=["text"]
            ),
            Back(Const("⬅️ Назад")),
            state=EditWorkerState.edit_weekly_hours,
            getter=worker_edit_getter,
        ),
        Window(
            Const("Установите разрешения для сотрудника:"),
            Multiselect(
                checked_text=Format("✅ {item[0]}"),
                unchecked_text=Format("❌ {item[0]}"),
                items=[
                    ("Кастомные задачи", "custom_tasks"),
                    ("Непроектные задачи", "non_project_tasks"),
                ],
                id="perms_ms",
                item_id_getter=lambda x: x[1],
                default_checked="default_perms",
            ),
            Button(
                Const("💾 Сохранить"),
                id="save_perms",
                on_click=on_permissions_updated,
            ),
            Back(Const("⬅️ Назад")),
            state=EditWorkerState.edit_permissions,
            getter=worker_edit_getter,
        ),
        Window(
            Const("Выберите проекты для сотрудника:"),
            Multiselect(
                checked_text=Format("✅ {item[1]}"),
                unchecked_text=Format("❌ {item[1]}"),
                items="project_items",
                item_id_getter=lambda item: str(item[0]),
                id="projects_ms",
                default_checked="default_projects",
            ),
            Button(
                Const("💾 Сохранить"),
                id="save_projects",
                on_click=on_projects_updated,
            ),
            Back(Const("⬅️ Назад")),
            state=EditWorkerState.edit_projects,
            getter=worker_edit_getter,
        ),
        Window(
            Format(
                "Подтвердите изменения:\n\n"
                "{changes}\n\n"
            ),
            Button(
                Const("✅ Подтвердить изменения"),
                id="confirm_changes",
                on_click=save_worker_changes,
            ),
            Back(Const("⬅️ Назад")),
            Cancel(Const("❌ Отмена")),
            state=EditWorkerState.confirm,
            getter=confirm_getter,
        ),
    )