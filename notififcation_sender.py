from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict
from aiogram import Bot
import asyncio

from data.database import Database
from data.project_operations import ProjectOperations
from data.task_operations import TaskOperations
from data.time_entry_operations import TimeEntryOperations
from data.worker_operations import WorkerOperations


from message_sender import MessageSender


class NotificationSender:
    def __init__(self, bot: Bot, db: Database, message_sender: MessageSender):
        self.bot = bot
        self.db = db
        self.message_sender = message_sender
        self.timezone = timezone(timedelta(hours=3))
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)
        self.active_workers: Dict[int, asyncio.Task] = {}

    async def start(self):
        workers = WorkerOperations.get_all_workers(self.db)
        for worker in workers:
            self._setup_worker_schedule(worker)

        self.scheduler.start()
        print("Notification service started")

    def _setup_worker_schedule(self, worker: Dict):
        telegram_id = worker['telegram_id']
        if telegram_id in self.active_workers:
            self.active_workers[telegram_id].cancel()

        task = asyncio.create_task(self._setup_single_worker_schedule(worker))
        self.active_workers[telegram_id] = task

    async def _setup_single_worker_schedule(self, worker: Dict):
        reminder_day = worker['reminder_day']
        reminder_time = worker['reminder_time']

        day_map = {
            'понедельник': 'mon',
            'вторник': 'tue',
            'среда': 'wed',
            'четверг': 'thu',
            'пятница': 'fri',
            'суббота': 'sat',
            'воскресенье': 'sun'
        }

        cron_day = day_map.get(reminder_day.lower(), 'fri')
        hour, minute = map(int, str(reminder_time).split(':')[:2])

        trigger = CronTrigger(
            day_of_week=cron_day,
            hour=hour,
            minute=minute,
            timezone=self.timezone
        )

        job = self.scheduler.add_job(
            self._send_weekly_report,
            trigger=trigger,
            args=[worker['id']],
            id=f"worker_{worker['id']}_weekly_report",
            replace_existing=True
        )

        now = datetime.now(self.timezone)
        next_run = job.next_run_time
        time_until = next_run - now
        hours_until = time_until.total_seconds() / 3600

        print(f"\nНастроено оповещение для работника {worker['id']} ({worker.get('name', '')}):")
        print(f"День недели: {reminder_day} ({cron_day})")
        print(f"Время: {reminder_time}")
        print(f"Следующее оповещение: {next_run.strftime('%Y-%m-%d %H:%M')} (МСК)")
        print(f"Через {hours_until:.1f} часов ({time_until})")
        print("-" * 40)

    async def _send_weekly_report(self, worker_id: int):
        worker = WorkerOperations.get_worker(self.db, worker_id)
        if not worker:
            print("Worker not found")
            return

        report = ["Ваш еженедельный отчет:\n"]
        today = datetime.now(self.timezone).date()
        start_of_week = today - timedelta(days=today.weekday())

        project_report = await self._generate_report(
            worker_id,
            datetime.combine(start_of_week, datetime.min.time()).replace(tzinfo=self.timezone),
            datetime.combine(today, datetime.max.time()).replace(tzinfo=self.timezone)
        )

        report.append(project_report)

        await self._send_message(worker['telegram_id'], "\n".join(report))

    async def _generate_report(self, worker_id: int, start_date: datetime,
                               end_date: datetime) -> str:
        all_time_entries = TimeEntryOperations.get_time_entries(
            self.db,
            worker_id,
            start_date=start_date,
            end_date=end_date
        )

        projects_data = {}
        total_week_hours = 0.0

        for entry in all_time_entries:
            project_id = entry['project_id']
            if project_id not in projects_data:
                project = ProjectOperations.get_project(self.db, project_id)
                projects_data[project_id] = {
                    'name': project['name'],
                    'total_hours': 0,
                    'tasks': {}
                }

            task_id = entry['task_id']
            if task_id not in projects_data[project_id]['tasks']:
                task = TaskOperations.get_task(self.db, task_id)
                projects_data[project_id]['tasks'][task_id] = {
                    'name': task['name'],
                    'font_name': entry.get('font_name', ''),
                    'hours': 0
                }

            projects_data[project_id]['tasks'][task_id]['hours'] += entry['hours']
            projects_data[project_id]['total_hours'] += entry['hours']
            total_week_hours += entry['hours']

        report_lines = []

        for project_id, project_data in projects_data.items():
            report_lines.append(f"\n{project_data['name']}:")

            for task_id, task_data in project_data['tasks'].items():
                if task_data['hours'] > 0:
                    report_lines.append(
                        f" - {task_data['name']}|{task_data['font_name']}: {task_data['hours']:.1f} ч."
                    )

            report_lines.append(f" Всего: {project_data['total_hours']:.1f} ч.")

        if not report_lines:
            return "\nНет данных о затраченном времени за указанный период."

        report_lines.append(f"\nОбщее количество часов за неделю: {total_week_hours:.1f} ч.")

        return "\n".join(report_lines)

    async def _send_message(self, telegram_id: int, text: str):
        try:
            await self.message_sender.send_message(telegram_id, text)
        except Exception as e:
            print(f"Failed to send message to {telegram_id}: {e}")

    async def on_data_changed(self, worker_id: int):
        worker = WorkerOperations.get_worker(self.db, worker_id)
        self._setup_worker_schedule(worker)
        await self._send_weekly_report(worker_id)

    async def stop(self):
        self.scheduler.shutdown()
        for task in self.active_workers.values():
            task.cancel()
        await asyncio.gather(*self.active_workers.values(), return_exceptions=True)
        print("Notification service stopped")
