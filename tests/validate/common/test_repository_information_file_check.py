import pytest
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.validate.common.repository_information_file import (
    RepositoryInformationFile,
)
from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_no_info_file():
    repository = dummy_repository_base()
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_no_readme_file():
    repository = dummy_repository_base()
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_has_info_file():
    repository = dummy_repository_base()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "info", "type": "file"}, "test/test", "master"
        )
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_info_md_file():
    repository = dummy_repository_base()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "info.md", "type": "file"}, "test/test", "master"
        )
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_readme_file():
    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "readme", "type": "file"}, "test/test", "master"
        )
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed


@pytest.mark.asyncio
async def test_has_readme_md_file():
    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "readme.md", "type": "file"}, "test/test", "master"
        )
    ]
    check = RepositoryInformationFile(repository)
    await check._async_run_check()
    assert not check.failed
