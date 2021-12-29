""""Hacs base setup task."""
# pylint: disable=abstract-method
from __future__ import annotations

from datetime import timedelta
from logging import Handler
from time import monotonic

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsStage


class HacsTask:
    """Hacs task base."""

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
                self.hacs.log.debug,
                f"Skipping task, HACS is disabled {self.hacs.system.disabled_reason}",
            )
            return
        self.task_logger(self.hacs.log.debug, "Executing task")
        start_time = monotonic()

        try:
            if task := getattr(self, "async_execute", None):
                await task()  # pylint: disable=not-callable
            elif task := getattr(self, "execute", None):
                await self.hass.async_add_executor_job(task)

        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.task_logger(self.hacs.log.error, f"failed: {exception}")

        else:
            self.hacs.log.debug(
                "HacsTask<%s> took %.3f seconds to complete", self.slug, monotonic() - start_time
            )
