import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_async_run_repository_checks(hacs: HacsBase, repository_integration):

    await hacs.validation.async_run_repository_checks(repository_integration)
    await hacs.hass.async_block_till_done()

    hacs.system.action = True
    hacs.system.running = True
    repository_integration.tree = []
    with pytest.raises(SystemExit):
        await hacs.validation.async_run_repository_checks(repository_integration)

    hacs.system.action = False
    await hacs.validation.async_run_repository_checks(repository_integration)
    hacs.system.running = False
