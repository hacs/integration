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
async def test_async_run_repository_checks(hacs, repository_integration):
    await async_run_repository_checks(repository_integration)

    hacs.system.action = True
    hacs.system.running = True
    repository_integration.tree = []
    with pytest.raises(SystemExit):
        await async_run_repository_checks(repository_integration)

    hacs.system.action = False
    SHARE["rules"] = {}
    await async_run_repository_checks(repository_integration)
    hacs.system.running = False
