from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.hacsjson import Validator

test_tree = [
    AIOGitHubAPIRepositoryTreeContent({"path": "hacs.json", "type": "file"}, "test/test", "main"),
    AIOGitHubAPIRepositoryTreeContent({"path": "README.md", "type": "file"}, "test/test", "main"),
]


@pytest.mark.asyncio
async def test_hacs_manifest_no_manifest(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_valid_manifest(repository):
    repository.tree = test_tree
    repository.tree.append(
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "docs/README.nb.md", "type": "file"}, "test/test", "main"
        ),
    )

    async def _async_get_hacs_json(_):
        return {"name": "test", "documentation": {"en": "README.md", "nb": "docs/README.nb.md"}}

    repository.async_get_hacs_json = _async_get_hacs_json

    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_invalid_manifest(repository):
    repository.tree = test_tree

    async def _async_get_hacs_json(_):
        return {"not": "valid"}

    repository.async_get_hacs_json = _async_get_hacs_json

    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_hacs_manifest_with_missing_filename(repository, caplog):
    repository.tree = test_tree
    repository.data.category = "integration"

    async def _async_get_hacs_json(_):
        return {"name": "test", "zip_release": True, "hacs": "0.0.0"}

    repository.async_get_hacs_json = _async_get_hacs_json

    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
    assert (
        "<Validation hacsjson> failed:  zip_release is True, but filename is not set (More info: https://hacs.xyz/docs/publish/include#check-hacs-manifest )"
        in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "documentation", [{"en": "HACS.md"}, {"en": "docs/README.md"}, {"sv": "docs/hacs/some_file.md"}]
)
async def test_hacs_manifest_with_missing_documentation(repository, caplog, documentation):
    repository.tree = test_tree
    repository.data.category = "integration"

    async def _async_get_hacs_json(_):
        return {"name": "test", "documentation": documentation}

    repository.async_get_hacs_json = _async_get_hacs_json

    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
    for language, filename in (documentation).items():
        assert (
            f"failed:  The '{filename}' file for the 'documentation[{language}]' key does not exist"
            in caplog.text
        )
