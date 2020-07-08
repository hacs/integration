import os
from abc import ABC
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.share import get_hacs

ACTION = "GITHUB_ACTION" in os.environ


class RepositoryCheckException(Exception):
    pass


class RepositoryCheck(ABC):
    def __init__(self, repository) -> None:
        self.repository = repository
        self.hacs = get_hacs()
        self.failed = False
        self.logger = getLogger(f"{repository.data.category}.check")

    async def _async_run_check(self):
        """DO NOT OVERRIDE THIS IN SUBCLASSES!"""
        if ACTION:
            self.logger.info(f"Running {self.__class__.__name__}")
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


class RepositoryActionCheck(RepositoryCheck):
    pass
