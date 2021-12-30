"""The QueueManager class."""
from __future__ import annotations

import asyncio
import time
from typing import Coroutine

from homeassistant.core import HomeAssistant

from ..exceptions import HacsExecutionStillInProgress
from .logger import get_hacs_logger

_LOGGER = get_hacs_logger()


class QueueManager:
    """The QueueManager class."""

    running = False
    queue: list[Coroutine] = []

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @property
    def pending_tasks(self) -> int:
        """Return a count of pending tasks in the queue."""
        return len(self.queue)

    @property
    def has_pending_tasks(self) -> bool:
        """Return a count of pending tasks in the queue."""
        return self.pending_tasks != 0

    def clear(self) -> None:
        """Clear the queue."""
        self.queue = []

    def add(self, task: Coroutine) -> None:
        """Add a task to the queue."""
        self.queue.append(self.hass.loop.create_task(task))

    async def execute(self, number_of_tasks: int | None = None) -> None:
        """Execute the tasks in the queue."""
        if self.running:
            _LOGGER.debug("Execution is allreay running")
            raise HacsExecutionStillInProgress
        if len(self.queue) == 0:
            _LOGGER.debug("The queue is empty")
            return

        self.running = True

        _LOGGER.debug("Checking out tasks to execute")
        local_queue = []

        if number_of_tasks:
            for task in self.queue[:number_of_tasks]:
                local_queue.append(task)
        else:
            for task in self.queue:
                local_queue.append(task)

        for task in local_queue:
            self.queue.remove(task)

        _LOGGER.debug("Starting queue execution for %s tasks", len(local_queue))
        start = time.time()
        await asyncio.gather(*local_queue)
        end = time.time() - start

        _LOGGER.debug(
            "Queue execution finished for %s tasks finished in %.2f seconds",
            len(local_queue),
            end,
        )
        if self.has_pending_tasks:
            _LOGGER.debug("%s tasks remaining in the queue", len(self.queue))
        self.running = False
