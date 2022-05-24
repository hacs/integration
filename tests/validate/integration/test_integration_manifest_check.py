from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.integration_manifest import Validator


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest(repository_integration):
    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_valid_manifest(repository_integration):
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "main"
        )
    ]

    async def _async_get_integration_manifest(_):
        return {
            "domain": "test",
            "documentation": "https://hacs.xyz",
            "issue_tracker": "https://hacs.xyz",
            "codeowners": ["test"],
            "name": "test",
            "version": "1.0.0",
        }

    repository_integration.async_get_integration_manifest = _async_get_integration_manifest

    check = Validator(repository_integration)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_invalid_manifest(repository_integration):
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "main"
        )
    ]

    async def _async_get_integration_manifest(_):
        return {"not": "valid"}

    repository_integration.async_get_integration_manifest = _async_get_integration_manifest
    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed
