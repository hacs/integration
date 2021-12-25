import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.validate import (
    async_initialize_rules,
    async_run_repository_checks,
    base,
)


@pytest.mark.asyncio
async def test_async_initialize_rules(hacs: HacsBase):

    await async_initialize_rules(hacs.hass)
    assert base.RULES != {}


@pytest.mark.asyncio
async def test_async_run_repository_checks(hacs: HacsBase, repository_integration):
    await async_run_repository_checks(hacs, repository_integration)

    hacs.system.action = True
    hacs.system.running = True
    repository_integration.tree = []
    with pytest.raises(SystemExit):
        await async_run_repository_checks(hacs, repository_integration)

    hacs.system.action = False
    base.RULES = {}
    await async_run_repository_checks(hacs, repository_integration)
    hacs.system.running = False
