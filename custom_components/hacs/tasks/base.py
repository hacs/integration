""""Hacs base setup task."""
# pylint: disable=abstract-method
from __future__ import annotations

from datetime import timedelta
from timeit import default_timer as timer

from homeassistant.core import HomeAssistant

from ..enums import HacsStage
from ..mixin import HacsMixin, LogMixin


class HacsTask(HacsMixin, LogMixin):
    """Hacs task base."""

    hass: HomeAssistant

    events: list[str] | None = None
    schedule: timedelta | None = None
    stages: list[HacsStage] | None = None

    def __init__(self) -> None:
        self.hass = self.hacs.hass

    @property
    def slug(self) -> str:
        """Return the check slug."""
        return self.__class__.__module__.rsplit(".", maxsplit=1)[-1]

    async def execute_task(self, *_, **__) -> None:
        """Execute the task defined in subclass."""
        if self.hacs.system.disabled:
            self.log.warning(
                "Skipping task %s, HACS is disabled - %s",
                self.slug,
                self.hacs.system.disabled_reason,
            )
            return
        self.log.info("Executing task: %s", self.slug)
        start_time = timer()

        try:
            if task := getattr(self, "execute", None):
                await self.hass.async_add_executor_job(task)
            elif task := getattr(self, "async_execute", None):
                await task()  # pylint: disable=not-callable
            else:
                raise NotImplementedError(f"{self.slug} does not have a execute method defined.")
        except BaseException as exception:  # pylint: disable=broad-except
            self.log.error("Task %s failed: %s", self.slug, exception)

        else:
            self.log.debug(
                "Task %s took " "%.2f seconds to complete",
                self.slug,
                timer() - start_time,
            )
