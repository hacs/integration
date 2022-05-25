from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.information import Validator


@pytest.mark.asyncio
async def test_no_info_file(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_no_readme_file(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_has_info_file(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "info", "type": "file"}, "test/test", "main")
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_info_md_file(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "info.md", "type": "file"}, "test/test", "main")
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_readme_file(repository):
    repository.repository_manifest.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "readme", "type": "file"}, "test/test", "main")
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_readme_md_file(repository):
    repository.repository_manifest.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "readme.md", "type": "file"}, "test/test", "main"
        )
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
