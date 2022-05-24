from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.hacs_manifest import Validator


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_valid_manifest(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "hacs.json", "type": "file"}, "test/test", "main"
        )
    ]

    async def _async_get_hacs_json(_):
        return {"name": "test"}

    repository.async_get_hacs_json = _async_get_hacs_json

    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_invalid_manifest(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "hacs.json", "type": "file"}, "test/test", "main"
        )
    ]

    async def _async_get_hacs_json(_):
        return {"not": "valid"}

    repository.async_get_hacs_json = _async_get_hacs_json

    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
