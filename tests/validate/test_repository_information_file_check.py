from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.validate.information import Validator


async def test_no_info_file(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_no_readme_file(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_has_info_file(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "info", "type": "file"}, "test/test", "main"),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_has_info_md_file(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "info.md", "type": "file"}, "test/test", "main"),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_has_readme_file(repository):
    repository.repository_manifest.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "readme", "type": "file"}, "test/test", "main"),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_has_readme_md_file(repository):
    repository.repository_manifest.render_readme = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "readme.md", "type": "file"}, "test/test", "main",
        ),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
