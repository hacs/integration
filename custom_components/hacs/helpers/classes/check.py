import os
from abc import ABC
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.share import get_hacs


class RepositoryCheckException(Exception):
    pass


class RepositoryCheck(ABC):
    def __init__(self, repository) -> None:
        self.repository = repository
        self.hacs = get_hacs()
        self.failed = False
        self.logger = getLogger(f"{repository.data.category}.check")

    @property
    def action(self):
        return "GITHUB_ACTION" in os.environ

    async def _async_run_check(self):
        """DO NOT OVVERIDE THIS IN SUBCLASSES!"""
        try:
            await self.hacs.hass.async_add_executor_job(self.check)
            await self.async_check()
        except RepositoryCheckException as exception:
            self.failed = True
            self.logger.error(exception)

    def check(self):
        pass

    async def async_check(self):
        pass
