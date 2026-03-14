import pytest

from custom_components.hacs.utils.repository_icon import (
    async_resolve_repository_icon_url,
    hosted_brand_icon_url,
    local_brand_icon_urls,
    official_brand_icon_url,
    repository_icon_api_path,
)

from tests.common import MockedResponse, ResponseMocker


async def test_async_resolve_repository_icon_url_prefers_hosted_icon(
    repository_integration,
    response_mocker: ResponseMocker,
):
    repository_integration.data.id = "123"
    repository_integration.data.domain = "test"
    repository_integration.data.full_name = "hacs-test-org/integration-basic"
    repository_integration.ref = "main"
    repository_integration.content.path.remote = "custom_components/example"

    hosted_url = official_brand_icon_url("test")
    local_url = local_brand_icon_urls(repository_integration)[0]

    response_mocker.add(hosted_url, MockedResponse(status=200))
    response_mocker.add(local_url, MockedResponse(status=200))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
        cache=repository_integration.hacs.common.repository_icon_urls,
    )

    assert resolved == hosted_url
    assert repository_integration.hacs.common.repository_icon_urls[("123", False)] == hosted_url


async def test_async_resolve_repository_icon_url_falls_back_to_local_brand_icon(
    repository_integration,
    response_mocker: ResponseMocker,
):
    repository_integration.data.id = "123"
    repository_integration.data.domain = "test"
    repository_integration.data.full_name = "hacs-test-org/integration-basic"
    repository_integration.ref = "main"
    repository_integration.content.path.remote = "custom_components"

    hosted_url = official_brand_icon_url("test", dark=True)
    local_urls = local_brand_icon_urls(repository_integration, dark=True)

    response_mocker.add(hosted_url, MockedResponse(status=404))
    for url in local_urls[:-1]:
        response_mocker.add(url, MockedResponse(status=404))
    response_mocker.add(local_urls[-1], MockedResponse(status=200))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
        dark=True,
    )

    assert resolved == local_urls[-1]


async def test_async_resolve_repository_icon_url_falls_back_to_placeholder_image(
    repository_integration,
    response_mocker: ResponseMocker,
):
    repository_integration.data.id = "123"
    repository_integration.data.domain = "test"
    repository_integration.data.full_name = "hacs-test-org/integration-basic"
    repository_integration.ref = "main"
    repository_integration.content.path.remote = "custom_components"

    hosted_dark_url = official_brand_icon_url("test", dark=True)
    hosted_light_url = official_brand_icon_url("test")
    local_urls = local_brand_icon_urls(repository_integration, dark=True)
    placeholder_url = hosted_brand_icon_url("test", dark=True)

    response_mocker.add(hosted_dark_url, MockedResponse(status=404))
    for url in local_urls:
        response_mocker.add(url, MockedResponse(status=404))
    response_mocker.add(hosted_light_url, MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
        dark=True,
    )

    assert resolved == placeholder_url


def test_local_brand_icon_urls_include_domain_specific_fallback_path(repository_integration):
    repository_integration.data.domain = "test"
    repository_integration.data.full_name = "hacs-test-org/integration-basic"
    repository_integration.ref = "main"
    repository_integration.content.path.remote = "custom_components"

    urls = local_brand_icon_urls(repository_integration, dark=True)

    assert urls == [
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/"
        "custom_components/brand/dark_icon.png",
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/"
        "custom_components/brand/icon.png",
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/"
        "custom_components/test/brand/dark_icon.png",
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/"
        "custom_components/test/brand/icon.png",
    ]


def test_repository_icon_api_path():
    assert repository_icon_api_path("123") == "/api/hacs/icon/123"
    assert repository_icon_api_path("123", dark=True) == "/api/hacs/icon/123?dark=1"
