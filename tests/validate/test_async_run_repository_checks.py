import pytest

from custom_components.hacs.share import get_hacs
from custom_components.hacs.validate import async_run_repository_checks
from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_async_run_repository_checks():
    hacs = get_hacs()
    repository = dummy_repository_integration()
    await async_run_repository_checks(repository)

    hacs.action = True
    hacs.system.running = True
    repository.tree = []
    with pytest.raises(SystemExit):
        await async_run_repository_checks(repository)

    hacs.action = False
    await async_run_repository_checks(repository)
    hacs.system.running = False
