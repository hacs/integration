from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.integration.integration_manifest import (
    IntegrationManifest,
)


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest(repository_integration):
    check = IntegrationManifest(repository_integration)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_manifest(repository_integration):
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "main"
        )
    ]
    check = IntegrationManifest(repository_integration)
    await check._async_run_check()
    assert not check.failed
