""""Hacs base setup task."""
# pylint: disable=abstract-method
from __future__ import annotations

from datetime import timedelta
from logging import Handler
from timeit import default_timer as timer

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsStage
from ..mixin import LogMixin


class HacsTask(LogMixin):
    """Hacs task base."""

    hass: HomeAssistant

    events: list[str] | None = None
    schedule: timedelta | None = None
    stages: list[HacsStage] | None = None
    _can_run_disabled = False  ## Set to True if task can run while disabled

    def __init__(self, hacs: HacsBase, hass: HomeAssistant) -> None:
        self.hacs = hacs
        self.hass = hass

    @property
    def slug(self) -> str:
        """Return the check slug."""
        return self.__class__.__module__.rsplit(".", maxsplit=1)[-1]

    def task_logger(self, handler: Handler, msg: str) -> None:
        """Log message from task"""
        handler("HacsTask<%s> %s", self.slug, msg)

    async def execute_task(self, *_, **__) -> None:
        """Execute the task defined in subclass."""
        if not self._can_run_disabled and self.hacs.system.disabled:
            self.task_logger(
                self.log.debug,
                f"Skipping task, HACS is disabled {self.hacs.system.disabled_reason}",
            )
            return
        self.task_logger(self.log.debug, "Executing task")
        start_time = timer()

        try:
            if task := getattr(self, "execute", None):
                await self.hass.async_add_executor_job(task)
            elif task := getattr(self, "async_execute", None):
                await task()  # pylint: disable=not-callable
        except BaseException as exception:  # pylint: disable=broad-except
            self.task_logger(self.log.error, f"failed: {exception}")

        else:
            self.task_logger(
                self.log.debug,
                f"took {str(timer() - start_time)[:5]} seconds to complete",
            )
