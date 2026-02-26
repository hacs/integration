from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
from custom_components.hacs.validate.brands import Validator

from tests.common import MockedResponse, ResponseMocker


async def test_added_to_brands(repository, response_mocker: ResponseMocker):
    """Test validation passes when domain is in brands repo."""
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        MockedResponse(content={"custom": ["test"]}),
    )
    repository.data.domain = "test"
    repository.tree = []
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_not_added_to_brands(repository, response_mocker: ResponseMocker):
    """Test validation fails when domain not in brands repo and no local icons."""
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json", MockedResponse(content={"custom": []}),
    )
    repository.data.domain = "test"
    repository.tree = []
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_local_brand_icons(repository, response_mocker: ResponseMocker):
    """Test validation passes when local brand icons exist."""
    # Mock response not needed as it shouldn't be called
    repository.data.domain = "test"
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/brand/icon.png", "type": "file"},
            "test/test",
            "main",
        ),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_local_brand_icons_with_hdpi(repository, response_mocker: ResponseMocker):
    """Test validation passes with both regular and hDPI icons."""
    repository.data.domain = "test"
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/brand/icon.png", "type": "file"},
            "test/test",
            "main",
        ),
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/brand/icon@2x.png", "type": "file"},
            "test/test",
            "main",
        ),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_no_local_icons_fallback_to_brands(repository, response_mocker: ResponseMocker):
    """Test fallback to brands repo when no local icons exist."""
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        MockedResponse(content={"custom": ["test"]}),
    )
    repository.data.domain = "test"
    # No icon files in tree
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/manifest.json", "type": "file"},
            "test/test",
            "main",
        ),
    ]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
