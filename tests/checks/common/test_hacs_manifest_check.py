import pytest
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.checks.common.hacs_manifest import HacsManifest
from custom_components.hacs.helpers.classes.check import RepositoryCheckException
from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest():
    repository = dummy_repository_base()
    check = HacsManifest(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_manifest():
    repository = dummy_repository_base()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "hacs.json", "type": "file"}, "test/test", "master"
        )
    ]
    check = HacsManifest(repository)
    await check._async_run_check()
    assert not check.failed
