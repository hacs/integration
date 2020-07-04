# pylint: disable=missing-docstring,invalid-name
import asyncio
import time
from datetime import timedelta

from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)

max_concurrent_tasks = asyncio.Semaphore(15)
sleeper = 5

logger = getLogger("factory")


class HacsTaskFactory:
    def __init__(self):
        self.tasks = []
        self.running = False

    async def execute(self):
        if not self.tasks:
            logger.debug("No tasks to execute")
            return
        if self.running:
            logger.debug("Already executing tasks")
            return
        try:
            self.running = True
            logger.info("Processing %s tasks", len(self.tasks))
            start = time.time()
            await asyncio.gather(*self.tasks)
            logger.info(
                "Task processing of %s tasks completed in %s seconds",
                len(self.tasks),
                timedelta(seconds=round(time.time() - start)).seconds,
            )
            self.tasks = []
            self.running = False
        except RuntimeError:
            logger.warning("RuntimeError, Clearing current tasks")
            self.tasks = []
            self.running = False

    async def safe_common_update(self, repository):
        async with max_concurrent_tasks:
            try:
                await repository.common_update()
            except (AIOGitHubAPIException, HacsException) as exception:
                logger.error("%s - %s", repository.data.full_name, exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)

    async def safe_update(self, repository):
        async with max_concurrent_tasks:
            try:
                await repository.update_repository()
            except (AIOGitHubAPIException, HacsException) as exception:
                logger.error("%s - %s", repository.data.full_name, exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)

    async def safe_register(self, repo, category):
        async with max_concurrent_tasks:
            try:
                await register_repository(repo, category)
            except (AIOGitHubAPIException, HacsException) as exception:
                logger.error("%s - %s", repo, exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)
