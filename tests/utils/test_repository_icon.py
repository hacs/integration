from __future__ import annotations

from homeassistant.const import CONF_ID

from custom_components.hacs.const import VERSION_STORAGE
from custom_components.hacs.utils.repository_icon import (
    async_initialize_repository_icon_cache,
    async_resolve_repository_icon_url,
    hosted_brand_icon_url,
    local_brand_icon_urls,
    official_brand_icon_url,
    repository_icon_api_path,
)
from custom_components.hacs.utils.store import async_load_from_store

from tests.common import MockedResponse, ResponseMocker


class FakeImageCollection:
    def __init__(self) -> None:
        self._counter = 0
        self.created: list[dict] = []
        self.data: dict[str, dict] = {}
        self.deleted: list[str] = []

    async def async_create_item(self, data: dict) -> dict:
        file_field = data["file"]
        file_field.file.seek(0)
        self._counter += 1
        image_id = f"image_{self._counter}"
        while image_id in self.data:
            self._counter += 1
            image_id = f"image_{self._counter}"
        item = {
            CONF_ID: image_id,
            "content": file_field.file.read(),
            "content_type": file_field.content_type,
            "name": file_field.filename,
        }
        self.data[image_id] = item
        self.created.append(item)
        return item

    async def async_delete_item(self, image_id: str) -> None:
        self.deleted.append(image_id)
        self.data.pop(image_id, None)


def _configure_repository_icon_source(repository_integration) -> None:
    repository_integration.data.id = "123"
    repository_integration.data.domain = "test"
    repository_integration.data.full_name = "hacs-test-org/integration-basic"
    repository_integration.ref = "main"
    repository_integration.content.path.remote = "custom_components/test"


async def test_async_resolve_repository_icon_url_prefers_hosted_icon(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)

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


async def test_async_resolve_repository_icon_url_caches_local_brand_icon_in_image_upload(
    repository_integration,
    response_mocker: ResponseMocker,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    repository_integration.hacs.hass.data["image_upload"] = image_collection

    hosted_url = official_brand_icon_url("test")
    local_url = local_brand_icon_urls(repository_integration)[0]

    response_mocker.add(hosted_url, MockedResponse(status=404))
    response_mocker.add(
        local_url,
        MockedResponse(
            status=200,
            content=b"png-bytes",
            headers={"Content-Type": "image/png"},
        ),
    )

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == "/api/image/serve/image_1/original"
    assert resolved != local_url
    assert image_collection.created == [
        {
            "id": "image_1",
            "content": b"png-bytes",
            "content_type": "image/png",
            "name": "icon.png",
        }
    ]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {
        "123:false": {
            "image_id": "image_1",
            "source_url": local_url,
        }
    }


async def test_async_resolve_repository_icon_url_reuses_uploaded_icon_when_source_is_unchanged(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"cached",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    local_url = local_brand_icon_urls(repository_integration)[0]
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            "source_url": local_url,
        }
    }

    response_mocker.add(official_brand_icon_url("test"), MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == "/api/image/serve/image_1/original"
    assert image_collection.created == []


async def test_async_resolve_repository_icon_url_replaces_uploaded_icon_when_source_changes(
    repository_integration,
    response_mocker: ResponseMocker,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"old",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection

    old_local_url = local_brand_icon_urls(repository_integration)[0]
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            "source_url": old_local_url,
        }
    }

    repository_integration.ref = "new-branch"
    new_local_url = local_brand_icon_urls(repository_integration)[0]

    response_mocker.add(official_brand_icon_url("test"), MockedResponse(status=404))
    response_mocker.add(
        new_local_url,
        MockedResponse(
            status=200,
            content=b"new-png",
            headers={"Content-Type": "image/png"},
        ),
    )

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == "/api/image/serve/image_2/original"
    assert image_collection.deleted == ["image_1"]
    assert image_collection.created == [
        {
            "id": "image_2",
            "content": b"new-png",
            "content_type": "image/png",
            "name": "icon.png",
        }
    ]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {
        "123:false": {
            "image_id": "image_2",
            "source_url": new_local_url,
        }
    }


async def test_async_resolve_repository_icon_url_clears_uploaded_icon_when_placeholder_wins(
    repository_integration,
    response_mocker: ResponseMocker,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"old",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    old_local_url = local_brand_icon_urls(repository_integration)[0]
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            "source_url": old_local_url,
        }
    }

    repository_integration.ref = "new-branch"
    current_local_url = local_brand_icon_urls(repository_integration)[0]

    response_mocker.add(official_brand_icon_url("test"), MockedResponse(status=404))
    response_mocker.add(current_local_url, MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == hosted_brand_icon_url("test")
    assert image_collection.deleted == ["image_1"]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {}


async def test_async_initialize_repository_icon_cache_prunes_removed_repositories(
    repository_integration,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"current",
        "content_type": "image/png",
        "name": "icon.png",
    }
    image_collection.data["image_2"] = {
        "content": b"stale",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    hass_storage["hacs.repository_icons"] = {
        "version": VERSION_STORAGE,
        "data": {
            "123:false": {
                "image_id": "image_1",
                "source_url": "https://example.com/icon.png",
            },
            "999:false": {
                "image_id": "image_2",
                "source_url": "https://example.com/stale.png",
            },
        },
    }

    repository_integration.hacs.repositories.register(repository_integration)
    await async_initialize_repository_icon_cache(repository_integration.hacs)

    assert repository_integration.hacs.common.repository_uploaded_icons == {
        "123:false": {
            "image_id": "image_1",
            "source_url": "https://example.com/icon.png",
        }
    }
    assert image_collection.deleted == ["image_2"]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {
        "123:false": {
            "image_id": "image_1",
            "source_url": "https://example.com/icon.png",
        }
    }


async def test_async_resolve_repository_icon_url_falls_back_to_placeholder_image(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)

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
    _configure_repository_icon_source(repository_integration)
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
