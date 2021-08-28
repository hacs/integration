"""Hacs task manager."""
from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path

from ..mixin import HacsMixin, LogMixin
from .base import HacsTask


class HacsTaskManager(HacsMixin, LogMixin):
    """Hacs task manager."""

    def __init__(self) -> None:
        """Initialize the setup manager class."""
        self.__tasks: dict[str, HacsTask] = {}

    @property
    def tasks(self) -> list[HacsTask]:
        """Return all list of all tasks."""
        return list(self.__tasks.values())

    async def async_load(self) -> None:
        """Load all tasks."""
        task_files = Path(__file__).parent
        task_modules = (
            module.stem
            for module in task_files.glob("*.py")
            if module.name not in ("base.py", "__init__.py", "manager.py")
        )

        async def _load_module(module: str):
            task_module = import_module(f"{__package__}.{module}")
            if task := await task_module.async_setup():
                self.__tasks[task.slug] = task

        await asyncio.gather(*[_load_module(task) for task in task_modules])
        self.log.info("Loaded %s tasks", len(self.tasks))
        self.register_event_handlers()
        self.register_scheduled_handlers()

    def register_event_handlers(self) -> None:
        """Register event handlers."""
        for task in self.tasks:
            if task.events is not None:
                for event in task.events:
                    self.hacs.hass.bus.async_listen_once(event, task.execute_task)

    def register_scheduled_handlers(self) -> None:
        """Register event handlers."""
        for task in self.hacs.recuring_tasks:
            task()
        for task in self.tasks:
            if task.schedule is not None:
                self.hacs.recuring_tasks.append(
                    self.hacs.hass.helpers.event.async_track_time_interval(
                        task.execute_task, task.schedule
                    )
                )

    def get(self, slug: str) -> HacsTask | None:
        """Return a task."""
        return self.__tasks.get(slug)

    async def async_execute_runtume_tasks(self) -> None:
        """Execute the the execute methods of each runtime task if the stage matches."""
        await asyncio.gather(
            *(
                task.execute_task()
                for task in self.tasks
                if task.stages is not None and self.hacs.stage in task.stages
            )
        )
