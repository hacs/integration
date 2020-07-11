import pytest
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.validate.integration.integration_manifest import (
    IntegrationManifest,
)
from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest():
    repository = dummy_repository_integration()
    check = IntegrationManifest(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_manifest():
    repository = dummy_repository_integration()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "master"
        )
    ]
    check = IntegrationManifest(repository)
    await check._async_run_check()
    assert not check.failed
