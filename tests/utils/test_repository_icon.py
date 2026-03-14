from custom_components.hacs.utils.repository_icon import (
    async_resolve_repository_icon_url,
    hosted_brand_icon_url,
    local_brand_icon_urls,
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

    hosted_url = hosted_brand_icon_url("test")
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
    repository_integration.content.path.remote = "custom_components/example"

    dark_hosted_url = hosted_brand_icon_url("test", dark=True)
    dark_local_url, local_url = local_brand_icon_urls(repository_integration, dark=True)

    response_mocker.add(dark_hosted_url, MockedResponse(status=404))
    response_mocker.add(dark_local_url, MockedResponse(status=404))
    response_mocker.add(local_url, MockedResponse(status=200))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
        dark=True,
    )

    assert resolved == local_url


def test_repository_icon_api_path():
    assert repository_icon_api_path("123") == "/api/hacs/icon/123"
    assert repository_icon_api_path("123", dark=True) == "/api/hacs/icon/123?dark=1"
