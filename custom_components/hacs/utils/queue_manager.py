"""The QueueManager class."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
import time
from typing import Coroutine

from homeassistant.core import HomeAssistant

from ..exceptions import HacsExecutionStillInProgress
from .logger import LOGGER

_LOGGER = LOGGER


class QueueManager:
    """The QueueManager class."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.queue: list[list[Coroutine]] = []
        self.running = False

    @property
    def pending_tasks(self) -> int:
        """Return a count of pending tasks in the queue."""
        return sum(len(item) for item in self.queue)

    @property
    def has_pending_tasks(self) -> bool:
        """Return if there are pending tasks in the queue."""
        return self.pending_tasks != 0

    def clear(self) -> None:
        """Clear the queue."""
        self.queue = []

    def add(self, tasks: Iterable[Coroutine]) -> None:
        """Add a task to the queue."""
        self.queue.append(list(tasks))

    async def execute(self, number_of_tasks: int | None = None) -> None:
        """Execute the tasks in the queue."""
        if self.running:
            _LOGGER.debug("<QueueManager> Execution is already running")
            raise HacsExecutionStillInProgress
        if len(self.queue) == 0:
            _LOGGER.debug("<QueueManager> The queue is empty")
            return

        self.running = True

        while self.queue and (number_of_tasks is None or number_of_tasks):
            _LOGGER.debug("<QueueManager> Checking out tasks to execute")
            local_queue = []
            queue_item = self.queue[0]

            if number_of_tasks:
                for task in queue_item[:number_of_tasks]:
                    local_queue.append(task)
                    number_of_tasks -= 1
            else:
                for task in queue_item:
                    local_queue.append(task)

            for task in local_queue:
                queue_item.remove(task)
            if not queue_item:
                self.queue.remove(queue_item)

            _LOGGER.debug("<QueueManager> Starting queue execution for %s tasks", len(local_queue))
            start = time.time()
            result = await asyncio.gather(*local_queue, return_exceptions=True)
            for entry in result:
                if isinstance(entry, Exception):
                    _LOGGER.error("<QueueManager> %s", entry)
            end = time.time() - start

            _LOGGER.debug(
                "<QueueManager> Queue execution finished for %s tasks finished in %.2f seconds",
                len(local_queue),
                end,
            )

        if self.has_pending_tasks:
            _LOGGER.debug("<QueueManager> %s tasks remaining in the queue", self.pending_tasks)
        self.running = False
