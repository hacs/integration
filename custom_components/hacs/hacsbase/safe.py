# pylint: disable=missing-docstring,invalid-name
import asyncio
from aiogithubapi import AIOGitHubException

max_concurrent_tasks = asyncio.Semaphore(15)


async def safe_common_update(repository):
    async with max_concurrent_tasks:
        try:
            await repository.common_update()
        except AIOGitHubException:
            pass

        # Due to GitHub ratelimits we need to sleep a bit
        await asyncio.sleep(5)


async def safe_update(repository):
    async with max_concurrent_tasks:
        try:
            await repository.update_repository()
        except AIOGitHubException:
            pass

        # Due to GitHub ratelimits we need to sleep a bit
        await asyncio.sleep(5)


async def safe_register(hacs, repo, category):
    async with max_concurrent_tasks:
        try:
            await hacs.register_repository(repo, category)
        except AIOGitHubException:
            pass

        # Due to GitHub ratelimits we need to sleep a bit
        await asyncio.sleep(5)
