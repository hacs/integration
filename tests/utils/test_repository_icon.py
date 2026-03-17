from __future__ import annotations

from pathlib import Path

from homeassistant.const import CONF_ID

from custom_components.hacs.const import VERSION_STORAGE
from custom_components.hacs.update import HacsRepositoryUpdateEntity
from custom_components.hacs.utils.repository_icon import (
    async_initialize_repository_icon_cache,
    async_resolve_repository_icon_url,
    hosted_brand_icon_url,
    integration_brand_icon_api_path,
    local_brand_icon_paths,
    official_brand_icon_urls,
    remote_brand_icon_urls,
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
    repository_integration.content.path.local = repository_integration.localpath
    repository_integration.data.installed = True


def _write_local_brand_icon(
    repository_integration,
    *,
    filename: str = "icon.png",
    content: bytes = b"png-bytes",
) -> None:
    path = local_brand_icon_paths(repository_integration, dark=filename == "dark_icon.png")[0]
    if path.name != filename:
        path = path.with_name(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


async def test_update_entity_picture_uses_core_brands_api_path(repository_integration):
    _configure_repository_icon_source(repository_integration)

    entity = HacsRepositoryUpdateEntity(
        hacs=repository_integration.hacs,
        repository=repository_integration,
    )

    assert entity.entity_picture == integration_brand_icon_api_path("test")


async def test_async_resolve_repository_icon_url_prefers_hosted_icon(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    _write_local_brand_icon(repository_integration)
    hosted_url = official_brand_icon_urls("test")[0]
    response_mocker.add(hosted_url, MockedResponse(status=200))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == hosted_url


async def test_async_resolve_repository_icon_url_uses_core_brand_handler_for_local_icon(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    _write_local_brand_icon(repository_integration)
    response_mocker.add(official_brand_icon_urls("test")[0], MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == integration_brand_icon_api_path("test")


async def test_async_resolve_repository_icon_url_fetches_remote_brand_icon_when_not_installed(
    repository_integration,
    response_mocker: ResponseMocker,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    repository_integration.content.path.local = None
    repository_integration.data.installed = False
    image_collection = FakeImageCollection()
    repository_integration.hacs.hass.data["image_upload"] = image_collection

    hosted_url = official_brand_icon_urls("test")[0]
    remote_url = remote_brand_icon_urls(repository_integration)[0]
    response_mocker.add(hosted_url, MockedResponse(status=404))
    response_mocker.add(
        remote_url,
        MockedResponse(content=b"remote-png", headers={"Content-Type": "image/png"}),
    )

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == "/api/image/serve/image_1/original"
    assert image_collection.created == [
        {
            "id": "image_1",
            "content": b"remote-png",
            "content_type": "image/png",
            "name": "icon.png",
        }
    ]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {
        "123:false": {
            "image_id": "image_1",
            "source_url": remote_url,
        }
    }


async def test_async_resolve_repository_icon_url_reuses_cached_remote_icon_when_not_installed(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    repository_integration.content.path.local = None
    repository_integration.data.installed = False
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"cached-remote",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            "source_url": remote_brand_icon_urls(repository_integration)[0],
        }
    }

    response_mocker.add(official_brand_icon_urls("test")[0], MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == "/api/image/serve/image_1/original"
    assert image_collection.created == []


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
                "source_url": remote_brand_icon_urls(repository_integration)[0],
            },
            "999:false": {
                "image_id": "image_2",
                "source_url": "https://raw.githubusercontent.com/example/icon.png",
            },
        },
    }

    repository_integration.hacs.repositories.register(repository_integration)
    await async_initialize_repository_icon_cache(repository_integration.hacs)

    assert repository_integration.hacs.common.repository_uploaded_icons == {
        "123:false": {
            "image_id": "image_1",
            "source_url": remote_brand_icon_urls(repository_integration)[0],
        }
    }
    assert image_collection.deleted == ["image_2"]


async def test_async_initialize_repository_icon_cache_restores_remote_entries(
    repository_integration,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"remote",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    remote_url = remote_brand_icon_urls(repository_integration)[0]
    hass_storage["hacs.repository_icons"] = {
        "version": VERSION_STORAGE,
        "data": {
            "123:false": {
                "image_id": "image_1",
                "source_url": remote_url,
            }
        },
    }

    repository_integration.hacs.repositories.register(repository_integration)
    await async_initialize_repository_icon_cache(repository_integration.hacs)

    assert repository_integration.hacs.common.repository_uploaded_icons == {
        "123:false": {
            "image_id": "image_1",
            "source_url": remote_url,
        }
    }


async def test_async_resolve_repository_icon_url_falls_back_to_placeholder_image(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    repository_integration.content.path.local = None
    repository_integration.data.installed = False

    response_mocker.add(official_brand_icon_urls("test", dark=True)[0], MockedResponse(status=404))
    response_mocker.add(official_brand_icon_urls("test", dark=True)[1], MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
        dark=True,
    )

    assert resolved == hosted_brand_icon_url("test", dark=True)


def test_local_brand_icon_paths_use_installed_custom_component_directory(repository_integration):
    _configure_repository_icon_source(repository_integration)

    paths = local_brand_icon_paths(repository_integration, dark=True)

    assert paths == [
        Path(repository_integration.localpath) / "brand" / "dark_icon.png",
        Path(repository_integration.localpath) / "brand" / "icon.png",
    ]


def test_remote_brand_icon_urls_use_repository_remote_path(repository_integration):
    _configure_repository_icon_source(repository_integration)

    urls = remote_brand_icon_urls(repository_integration, dark=True)

    assert urls == [
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/custom_components/test/brand/dark_icon.png",
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/custom_components/test/brand/icon.png",
    ]


def test_repository_icon_api_path():
    assert repository_icon_api_path("123") == "/api/hacs/icon/123"
    assert repository_icon_api_path("123", dark=True) == "/api/hacs/icon/123?dark=1"
