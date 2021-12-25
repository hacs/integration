from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository

RULES: dict[str, list[ValidationBase]] = {}


class ValidationException(Exception):
    pass


class ValidationBase:
    action_only = False

    def __init__(self, repository: HacsRepository) -> None:
        self.hacs = repository.hacs
        self.repository = repository
        self.failed = False
        self.logger = repository.logger

    def __init_subclass__(cls, category="common", **kwargs) -> None:
        """Initialize a subclass, register if possible."""
        super().__init_subclass__(**kwargs)
        if RULES.get(category) is None:
            RULES[category] = []
        if cls not in RULES[category]:
            RULES[category].append(cls)

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
