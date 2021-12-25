from __future__ import annotations

from typing import TYPE_CHECKING

from ..share import SHARE, get_hacs

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository


class ValidationException(Exception):
    pass


class ValidationBase:
    action_only = False

    def __init__(self, repository: HacsRepository) -> None:
        self.hacs = get_hacs()
        self.repository = repository
        self.failed = False
        self.logger = repository.logger

    def __init_subclass__(cls, category="common", **kwargs) -> None:
        """Initialize a subclass, register if possible."""
        super().__init_subclass__(**kwargs)
        if SHARE["rules"].get(category) is None:
            SHARE["rules"][category] = []
        if cls not in SHARE["rules"][category]:
            SHARE["rules"][category].append(cls)

    async def _async_run_check(self):
        """DO NOT OVERRIDE THIS IN SUBCLASSES!"""
        if self.hacs.system.action:
            self.logger.info(f"Running check '{self.__class__.__name__}'")
        try:
            await self.hacs.hass.async_add_executor_job(self.check)
            await self.async_check()
        except ValidationException as exception:
            self.failed = True
            self.logger.error(exception)

    def check(self):
        pass

    async def async_check(self):
        pass


class ActionValidationBase(ValidationBase):
    action_only = True
