"""The QueueManager class."""
from __future__ import annotations

import asyncio
import time
from typing import Coroutine

from ..exceptions import HacsExecutionStillInProgress
from .logger import LOGGER


class QueueManager:
    """The QueueManager class."""

    def __init__(self) -> None:
        self._queue: list[asyncio.Task] = []
        self._execution_group: asyncio.Future | None = None
        self._stopping = False

    @property
    def running(self) -> bool:
        """Return a bool indicating if we are already running."""
        return self._execution_group is not None

    @property
    def pending_tasks(self) -> int:
        """Return a count of pending tasks in the queue."""
        return len(self._queue)

    @property
    def has_pending_tasks(self) -> bool:
        """Return a count of pending tasks in the queue."""
        return self.pending_tasks != 0

    def clear(self) -> None:
        """Clear the queue."""
        self._stopping = True
        for task in self._queue:
            task.cancel()
        if self._execution_group is not None:
            self._execution_group.cancel()
            self._execution_group = None
        self._queue = []
        self._stopping = False

    def add(self, task: Coroutine) -> None:
        """Add a task to the queue."""
        _task = asyncio.create_task(task)
        if self._stopping:
            _task.cancel()
            return
        self._queue.append(_task)

    async def execute(self, number_of_tasks: int | None = None) -> None:
        """Execute the tasks in the queue."""
        if self.running:
            LOGGER.debug("<QueueManager> Execution is already running")
            raise HacsExecutionStillInProgress
        if self.pending_tasks == 0:
            LOGGER.debug("<QueueManager> The queue is empty")
            return
        if self._stopping:
            LOGGER.debug("<QueueManager> The queue is stopping")
            return

        LOGGER.debug("<QueueManager> Checking out tasks to execute")
        local_queue: list[asyncio.Task] = []

        for task in self._queue[:number_of_tasks]:
            local_queue.append(task)
            self._queue.remove(task)

        local_queue_count = len(local_queue)

        LOGGER.debug("<QueueManager> Starting queue execution for %s tasks", local_queue_count)
        start = time.time()
        self._execution_group = asyncio.gather(*local_queue, return_exceptions=True)
        result = await self._execution_group
        for entry in result:
            if isinstance(entry, Exception):
                LOGGER.error("<QueueManager> %s", entry)
        end = time.time() - start

        LOGGER.debug(
            "<QueueManager> Queue execution finished for %s tasks finished in %.2f seconds",
            local_queue_count,
            end,
        )
        if self.has_pending_tasks:
            LOGGER.debug("<QueueManager> %s tasks remaining in the queue", self.pending_tasks)
        self._execution_group = None
