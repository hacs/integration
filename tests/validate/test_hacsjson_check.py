from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.validate.hacsjson import Validator

test_tree = [
    AIOGitHubAPIRepositoryTreeContent(
        attributes={"path": "hacs.json", "type": "file"},
        repository="test/test",
        ref="main"),
    AIOGitHubAPIRepositoryTreeContent(
        attributes={"path": "README.md", "type": "file"},
        repository="test/test",
        ref="main"),
]


async def test_hacs_manifest_no_manifest(repository, caplog):
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
    assert "no 'hacs.json'" in caplog.text


async def test_hacs_manifest_with_valid_manifest(repository):
    repository.tree = test_tree
    repository.data.category = "integration"

    async def _async_get_hacs_json_raw(**_):
        return {"name": "test"}

    repository.get_hacs_json_raw = _async_get_hacs_json_raw

    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_hacs_manifest_with_invalid_manifest(repository):
    repository.tree = test_tree

    async def _async_get_hacs_json_raw(**_):
        return {"not": "valid"}

    repository.get_hacs_json_raw = _async_get_hacs_json_raw

    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_hacs_manifest_with_missing_filename(repository, caplog):
    repository.tree = test_tree
    repository.data.category = "integration"

    async def _async_get_hacs_json_raw(**_):
        return {"name": "test", "zip_release": True, "hacs": "0.0.0"}

    repository.get_hacs_json_raw = _async_get_hacs_json_raw

    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
    assert (
        "<Validation hacsjson> failed:  zip_release is True, but filename is not set (More info: https://hacs.xyz/docs/publish/include#check-hacs-manifest )"
        in caplog.text
    )


async def test_hacs_manifest_integration_zip_release_with_filename(repository):
    repository.tree = test_tree
    repository.data.category = "integration"

    async def _async_get_hacs_json_raw(**_):
        return {"name": "test", "zip_release": True, "filename": "file.zip"}

    repository.get_hacs_json_raw = _async_get_hacs_json_raw

    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
