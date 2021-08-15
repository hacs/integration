# pylint: disable=missing-docstring,invalid-name
import asyncio

from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.helpers.classes.exceptions import (
    HacsException,
    HacsNotModifiedException,
    HacsRepositoryArchivedException,
)
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.utils.logger import getLogger

max_concurrent_tasks = asyncio.Semaphore(15)
sleeper = 5

_LOGGER = getLogger()


class HacsTaskFactory:
    def __init__(self):
        self.tasks = []
        self.running = False

    async def safe_common_update(self, repository):
        async with max_concurrent_tasks:
            try:
                await repository.common_update()
            except HacsNotModifiedException:
                pass
            except (AIOGitHubAPIException, HacsException) as exception:
                _LOGGER.error("%s - %s", repository.data.full_name, exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)

    async def safe_update(self, repository):
        async with max_concurrent_tasks:
            try:
                await repository.update_repository()
            except HacsNotModifiedException:
                pass
            except HacsRepositoryArchivedException as exception:
                _LOGGER.warning("%s - %s", repository.data.full_name, exception)
            except (AIOGitHubAPIException, HacsException) as exception:
                _LOGGER.error("%s - %s", repository.data.full_name, exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)

    async def safe_register(self, repo, category):
        async with max_concurrent_tasks:
            try:
                await register_repository(repo, category)
            except (AIOGitHubAPIException, HacsException) as exception:
                _LOGGER.error("%s - %s", repo, exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)
