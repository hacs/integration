from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.common.repository_information_file import (
    RepositoryInformationFile,
)


@pytest.mark.asyncio
async def test_no_info_file(repository):
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_no_readme_file(repository):
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_has_info_file(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "info", "type": "file"}, "test/test", "main")
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_info_md_file(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "info.md", "type": "file"}, "test/test", "main")
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_readme_file(repository):
    repository.data.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "readme", "type": "file"}, "test/test", "main")
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_readme_md_file(repository):
    repository.data.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "readme.md", "type": "file"}, "test/test", "main"
        )
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed
