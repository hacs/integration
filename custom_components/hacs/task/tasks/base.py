""""Hacs base setup task."""
# pylint: disable=abstract-method
from __future__ import annotations

from abc import abstractmethod
from datetime import timedelta

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsStage
from custom_components.hacs.task.const import HacsTaskType
from custom_components.hacs.utils.bind_hacs import bind_hacs


@bind_hacs
class HacsTaskBase(HacsBase):
    """"Hacs task base."""

    @property
    def type(self) -> HacsTaskType:
        """Return the task type."""
        raise HacsTaskType.BASE

    @property
    def slug(self) -> str:
        """Return the check slug."""
        return self.__class__.__module__.rsplit(".", maxsplit=1)[-1]

    async def execute(self):
        """Execute the task."""
        raise NotImplementedError


class HacsTaskEventBase(HacsTaskBase):
    """"HacsTaskEventBase."""

    @property
    def type(self) -> HacsTaskType:
        """Return the task type."""
        return HacsTaskType.EVENT

    @property
    @abstractmethod
    def event(self) -> str:
        """Return the event to listen to."""
        raise NotImplementedError


class HacsTaskScheduleBase(HacsTaskBase):
    """"HacsTaskScheduleBase."""

    @property
    def type(self) -> HacsTaskType:
        """Return the task type."""
        return HacsTaskType.SCHEDULE

    @property
    @abstractmethod
    def schedule(self) -> timedelta:
        """Return the schedule."""
        raise NotImplementedError


class HacsTaskManualBase(HacsTaskBase):
    """"HacsTaskManualBase."""

    @property
    def type(self) -> HacsTaskType:
        """Return the task type."""
        return HacsTaskType.MANUAL


class HacsTaskRuntimeBase(HacsTaskBase):
    """"HacsTaskRuntimeBase."""

    @property
    def type(self) -> HacsTaskType:
        """Return the task type."""
        return HacsTaskType.RUNTIME

    @property
    def stages(self) -> list[HacsStage]:
        """Return a list of valid stages when this task can run."""
        return []
