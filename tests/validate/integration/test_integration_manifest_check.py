from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.integration_manifest import Validator


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest(repository_integration):
    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_manifest(repository_integration):
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "main"
        )
    ]
    check = Validator(repository_integration)
    await check.execute_validation()
    assert not check.failed
