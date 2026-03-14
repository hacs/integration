from __future__ import annotations

from pathlib import Path

from homeassistant.const import CONF_ID

from custom_components.hacs.const import VERSION_STORAGE
from custom_components.hacs.utils.repository_icon import (
    async_initialize_repository_icon_cache,
    async_resolve_repository_icon_url,
    hosted_brand_icon_url,
    local_brand_icon_paths,
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
    repository_integration.content.path.local = repository_integration.localpath


def _write_local_brand_icon(
    repository_integration,
    *,
    filename: str = "icon.png",
    content: bytes = b"png-bytes",
) -> Path:
    path = Path(repository_integration.localpath) / "brand" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _stored_local_source(path: Path) -> dict[str, str | int]:
    stat = path.stat()
    return {
        "source_path": path.as_posix(),
        "source_mtime_ns": stat.st_mtime_ns,
        "source_size": stat.st_size,
    }


async def test_async_resolve_repository_icon_url_prefers_hosted_icon(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    _write_local_brand_icon(repository_integration)

    hosted_url = official_brand_icon_url("test")
    response_mocker.add(hosted_url, MockedResponse(status=200))

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
    path = _write_local_brand_icon(repository_integration)
    image_collection = FakeImageCollection()
    repository_integration.hacs.hass.data["image_upload"] = image_collection

    response_mocker.add(official_brand_icon_url("test"), MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
    )

    assert resolved == "/api/image/serve/image_1/original"
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
            **_stored_local_source(path),
        }
    }


async def test_async_resolve_repository_icon_url_reuses_uploaded_icon_when_source_is_unchanged(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)
    path = _write_local_brand_icon(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"cached",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            **_stored_local_source(path),
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
    path = _write_local_brand_icon(repository_integration, content=b"new-png")
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"old",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            "source_path": path.with_name("old_icon.png").as_posix(),
            "source_mtime_ns": 1,
            "source_size": 3,
        }
    }

    response_mocker.add(official_brand_icon_url("test"), MockedResponse(status=404))

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
            **_stored_local_source(path),
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
    repository_integration.hacs.common.repository_uploaded_icons = {
        "123:false": {
            "image_id": "image_1",
            "source_path": "/tmp/icon.png",
            "source_mtime_ns": 1,
            "source_size": 3,
        }
    }

    response_mocker.add(official_brand_icon_url("test"), MockedResponse(status=404))

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
    path = _write_local_brand_icon(repository_integration, content=b"current")
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
                **_stored_local_source(path),
            },
            "999:false": {
                "image_id": "image_2",
                "source_path": "/tmp/stale.png",
                "source_mtime_ns": 1,
                "source_size": 5,
            },
        },
    }

    repository_integration.hacs.repositories.register(repository_integration)
    await async_initialize_repository_icon_cache(repository_integration.hacs)

    assert repository_integration.hacs.common.repository_uploaded_icons == {
        "123:false": {
            "image_id": "image_1",
            **_stored_local_source(path),
        }
    }
    assert image_collection.deleted == ["image_2"]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {
        "123:false": {
            "image_id": "image_1",
            **_stored_local_source(path),
        }
    }


async def test_async_initialize_repository_icon_cache_prunes_legacy_github_entries(
    repository_integration,
    hass_storage,
):
    _configure_repository_icon_source(repository_integration)
    image_collection = FakeImageCollection()
    image_collection.data["image_1"] = {
        "content": b"legacy",
        "content_type": "image/png",
        "name": "icon.png",
    }
    repository_integration.hacs.hass.data["image_upload"] = image_collection
    hass_storage["hacs.repository_icons"] = {
        "version": VERSION_STORAGE,
        "data": {
            "123:false": {
                "image_id": "image_1",
                "source_url": "https://raw.githubusercontent.com/example/icon.png",
            }
        },
    }

    repository_integration.hacs.repositories.register(repository_integration)
    await async_initialize_repository_icon_cache(repository_integration.hacs)

    assert repository_integration.hacs.common.repository_uploaded_icons == {}
    assert image_collection.deleted == ["image_1"]
    assert await async_load_from_store(repository_integration.hacs.hass, "repository_icons") == {}


async def test_async_resolve_repository_icon_url_falls_back_to_placeholder_image(
    repository_integration,
    response_mocker: ResponseMocker,
):
    _configure_repository_icon_source(repository_integration)

    hosted_dark_url = official_brand_icon_url("test", dark=True)
    hosted_light_url = official_brand_icon_url("test")
    placeholder_url = hosted_brand_icon_url("test", dark=True)

    response_mocker.add(hosted_dark_url, MockedResponse(status=404))
    response_mocker.add(hosted_light_url, MockedResponse(status=404))

    resolved = await async_resolve_repository_icon_url(
        repository_integration,
        repository_integration.hacs.session,
        dark=True,
    )

    assert resolved == placeholder_url


def test_local_brand_icon_paths_use_installed_custom_component_directory(repository_integration):
    _configure_repository_icon_source(repository_integration)

    paths = local_brand_icon_paths(repository_integration, dark=True)

    assert paths == [
        Path(repository_integration.localpath) / "brand" / "dark_icon.png",
        Path(repository_integration.localpath) / "brand" / "icon.png",
    ]


def test_repository_icon_api_path():
    assert repository_icon_api_path("123") == "/api/hacs/icon/123"
    assert repository_icon_api_path("123", dark=True) == "/api/hacs/icon/123?dark=1"
