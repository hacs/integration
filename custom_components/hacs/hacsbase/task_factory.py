# pylint: disable=missing-docstring,invalid-name
import logging
import time
from datetime import timedelta
import asyncio
from aiogithubapi import AIOGitHubException

max_concurrent_tasks = asyncio.Semaphore(15)
sleeper = 5

logger = logging.getLogger("hacs.factory")


class HacsTaskFactory:
    def __init__(self):
        self.tasks = []

    async def execute(self):
        if not self.tasks:
            logger.debug("No tasks to execute")
            return
        logger.info("Processing %s tasks", len(self.tasks))
        start = time.time()
        await asyncio.gather(*self.tasks)
        logger.info(
            "Task processing of %s tasks completed in %s seconds",
            len(self.tasks),
            timedelta(seconds=round(time.time() - start)).seconds,
        )
        self.tasks = []

    async def safe_common_update(self, repository):
        async with max_concurrent_tasks:
            try:
                await repository.common_update()
            except AIOGitHubException as exception:
                logger.error(exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)

    async def safe_update(self, repository):
        async with max_concurrent_tasks:
            try:
                await repository.update_repository()
            except AIOGitHubException as exception:
                logger.error(exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)

    async def safe_register(self, hacs, repo, category):
        async with max_concurrent_tasks:
            try:
                await hacs.register_repository(repo, category)
            except AIOGitHubException as exception:
                logger.error(exception)

            # Due to GitHub ratelimits we need to sleep a bit
            await asyncio.sleep(sleeper)
