import pytest
from custom_components.hacs.share import SHARE
from custom_components.hacs.validate import (
    async_initialize_rules,
    async_run_repository_checks,
)


@pytest.mark.asyncio
async def test_async_initialize_rules(hacs):

    await async_initialize_rules()


@pytest.mark.asyncio
async def test_async_run_repository_checks(hacs, repository):
    await async_run_repository_checks(repository)

    hacs.action = True
    hacs.system.running = True
    repository.tree = []
    with pytest.raises(SystemExit):
        await async_run_repository_checks(repository)

    hacs.action = False
    SHARE["rules"] = {}
    await async_run_repository_checks(repository)
    hacs.system.running = False
