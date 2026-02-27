from custom_components.hacs.repositories.base import HacsManifest
from custom_components.hacs.validate.brands import ASSET_FILENAME, Validator

from tests.common import MockedResponse, ResponseMocker


async def test_added_to_brands(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        MockedResponse(content={"custom": ["test"]}),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_not_added_to_brands(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json", MockedResponse(content={
                                                                        "custom": []}),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_local_brands_asset_content_in_root(repository):
    """Test that validation passes when the brands asset exists locally with content_in_root."""
    repository.repository_manifest = HacsManifest.from_dict(
        {"content_in_root": True})
    repository.treefiles = [f"brands/{ASSET_FILENAME}"]
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_local_brands_asset_not_in_root(repository):
    """Test that validation passes when the brands asset exists locally in a subdirectory."""
    repository.repository_manifest = HacsManifest.from_dict(
        {"content_in_root": False})
    repository.content.path.remote = "custom_components/test"
    repository.treefiles = [f"custom_components/test/brands/{ASSET_FILENAME}"]
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_local_brands_asset_missing_falls_back_to_remote(
    repository, response_mocker: ResponseMocker
):
    """Test that when local asset is missing, it falls back to checking the brands repo."""
    repository.repository_manifest = HacsManifest.from_dict(
        {"content_in_root": True})
    repository.treefiles = []
    repository.data.domain = "test"
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        MockedResponse(content={"custom": ["test"]}),
    )
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
