import pytest
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.share import get_hacs
from custom_components.hacs.helpers.functions.check import (
    async_run_repository_checks,
    load_repository_checks,
)
from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_async_run_repository_checks():
    hacs = get_hacs()
    repository = dummy_repository_integration()
    await async_run_repository_checks(repository)
    hacs.action = True
    load_repository_checks()
    repository.tree = []
    with pytest.raises(SystemExit):
        await async_run_repository_checks(repository)
    hacs.action = False
