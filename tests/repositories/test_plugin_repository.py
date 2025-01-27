"""Tests for specific plugin repository implementations."""

from collections.abc import Generator

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.repositories.plugin import HacsPluginRepository

from tests.common import get_hacs


@pytest.fixture
async def downloaded_plugin_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
) -> HacsPluginRepository:
    """Return a HacsPluginRepository instance."""
    hacs = get_hacs(hass)
    repository = hacs.repositories.get_by_full_name(
        "hacs-test-org/plugin-basic")
    await repository.async_install(version="1.0.0")
    return repository


@pytest.mark.parametrize(
    "repository_name, namespace",
    [
        ("hacs-test-org/plugin-basic", "/hacsfiles/plugin-basic"),
        ("hacs-test-org/plugin-advanced", "/hacsfiles/plugin-advanced"),
        ("hacs-test-org/awesome-plugin", "/hacsfiles/awesome-plugin"),
    ],
)
async def test_dashboard_namespace(
    downloaded_plugin_repository: HacsPluginRepository,
    repository_name: str,
    namespace: str,
) -> None:
    """Test the dashboard resource namespace."""
    downloaded_plugin_repository.data.full_name = repository_name
    assert downloaded_plugin_repository.generate_dashboard_resource_namespace() == namespace


@pytest.mark.parametrize(
    "downloaded, selected, available, expected",
    [
        (None, None, None, ""),
        ("1.0.0", None, None, "100"),
        (None, "2.0.1", None, "201"),
        (None, None, "3.4.2", "342"),
        ("1.7-dev09-r2", None, None, "17092"),
    ],
)
async def test_dashboard_hacstag(
    downloaded_plugin_repository: HacsPluginRepository,
    downloaded: str | None,
    selected: str | None,
    available: str | None,
    expected: str,
) -> None:
    """Test the dashboard resource hacstag."""
    downloaded_plugin_repository.data.installed_commit = None
    downloaded_plugin_repository.data.last_commit = None
    downloaded_plugin_repository.data.installed_version = downloaded
    downloaded_plugin_repository.data.last_version = available
    downloaded_plugin_repository.data.selected_tag = selected
    assert (
        downloaded_plugin_repository.generate_dashboard_resource_hacstag()
        == f"{downloaded_plugin_repository.data.id}{expected}"
    )


async def test_dashboard_url(downloaded_plugin_repository: HacsPluginRepository) -> None:
    """Test the dashboard resource url."""
    assert (
        downloaded_plugin_repository.generate_dashboard_resource_url()
        == "/hacsfiles/plugin-basic/plugin-basic.js?hacstag=1296267100"
    )


async def test_get_resource_handler(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler."""
    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is not None


async def test_get_resource_handler_wrong_version(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with wrong storage version."""
    try:
        hass.data["lovelace"].resources.store.version = 2
    except AttributeError:
        # Changed to 2025.2.0
        # Changed in https://github.com/home-assistant/core/pull/136313
        hass.data["lovelace"]["resources"].store.version = 2
    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "Can not use the dashboard resources" in caplog.text


async def test_get_resource_handler_wrong_key(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with wrong storage key."""
    try:
        hass.data["lovelace"].resources.store.key = "wrong_key"
    except AttributeError:
        # Changed to 2025.2.0
        # Changed in https://github.com/home-assistant/core/pull/136313
        hass.data["lovelace"]["resources"].store.key = "wrong_key"

    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "Can not use the dashboard resources" in caplog.text


async def test_get_resource_handler_none_store(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with store being none."""
    try:

        hass.data["lovelace"].resources.store = None
    except AttributeError:
        # Changed to 2025.2.0
        # Changed in https://github.com/home-assistant/core/pull/136313
        hass.data["lovelace"]["resources"].store = None
    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "YAML mode detected, can not update resources" in caplog.text


async def test_get_resource_handler_no_store(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with no store."""
    try:
        hass.data["lovelace"].resources.store = None
    except AttributeError:
        # Changed to 2025.2.0
        # Changed in https://github.com/home-assistant/core/pull/136313
        del hass.data["lovelace"]["resources"].store

    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "YAML mode detected, can not update resources" in caplog.text


async def test_get_resource_handler_no_lovelace_resources(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with no lovelace resources."""
    try:
        hass.data["lovelace"].resources = None
    except AttributeError:
        # Changed to 2025.2.0
        # Changed in https://github.com/home-assistant/core/pull/136313
        del hass.data["lovelace"]["resources"]
    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "Can not access the dashboard resources" in caplog.text


async def test_get_resource_handler_no_lovelace_data(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with no lovelace data."""
    del hass.data["lovelace"]
    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "Can not access the lovelace integration data" in caplog.text


async def test_get_resource_handler_no_hass_data(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the resource handler with no hass data."""
    hass_data = hass.data
    hass.data = None
    resources = downloaded_plugin_repository._get_resource_handler()
    assert resources is None
    assert "Can not access the hass data" in caplog.text
    hass.data = hass_data


async def test_remove_dashboard_resource(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test adding a dashboard resource."""
    resource_handler = downloaded_plugin_repository._get_resource_handler()
    await resource_handler.async_load()

    current_urls = [resource["url"]
                    for resource in resource_handler.async_items()]
    assert len(current_urls) == 1
    assert downloaded_plugin_repository.generate_dashboard_resource_url() in current_urls

    await downloaded_plugin_repository.remove_dashboard_resources()
    assert (
        "Removing dashboard resource /hacsfiles/plugin-basic/plugin-basic.js?hacstag=1296267100"
        in caplog.text
    )

    current_urls = [resource["url"]
                    for resource in resource_handler.async_items()]
    assert len(current_urls) == 0


async def test_add_dashboard_resource(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test adding a dashboard resource."""
    resource_handler = downloaded_plugin_repository._get_resource_handler()
    resource_handler.data.clear()

    current_urls = [resource["url"]
                    for resource in resource_handler.async_items()]
    assert len(current_urls) == 0

    await downloaded_plugin_repository.update_dashboard_resources()
    assert (
        "dding dashboard resource /hacsfiles/plugin-basic/plugin-basic.js?hacstag=1296267100"
        in caplog.text
    )


async def test_update_dashboard_resource(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test adding a dashboard resource."""
    resource_handler = downloaded_plugin_repository._get_resource_handler()
    await resource_handler.async_load()
    current_urls = [resource["url"]
                    for resource in resource_handler.async_items()]
    assert len(current_urls) == 1

    prev_url = downloaded_plugin_repository.generate_dashboard_resource_url()

    assert prev_url in current_urls
    assert current_urls[0] == prev_url

    downloaded_plugin_repository.data.installed_version = "1.1.0"
    await downloaded_plugin_repository.update_dashboard_resources()

    assert (
        "Updating existing dashboard resource from "
        "/hacsfiles/plugin-basic/plugin-basic.js?hacstag=1296267100 to "
        "/hacsfiles/plugin-basic/plugin-basic.js?hacstag=1296267110" in caplog.text
    )
    after_url = downloaded_plugin_repository.generate_dashboard_resource_url()
    assert after_url != prev_url

    current_urls = [resource["url"]
                    for resource in resource_handler.async_items()]
    assert len(current_urls) == 1
    assert current_urls[0] == after_url


async def test_add_dashboard_resource_with_invalid_file_name(
    hass: HomeAssistant,
    downloaded_plugin_repository: HacsPluginRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test adding a dashboard resource."""
    resource_handler = downloaded_plugin_repository._get_resource_handler()
    resource_handler.data.clear()

    current_urls = [resource["url"]
                    for resource in resource_handler.async_items()]
    assert len(current_urls) == 0

    downloaded_plugin_repository.data.file_name = "dist/plugin-basic.js"

    await downloaded_plugin_repository.update_dashboard_resources()
    assert "<Plugin hacs-test-org/plugin-basic> have defined an invalid file name dist/plugin-basic.js" in caplog.text
    assert (
        "Adding dashboard resource /hacsfiles/plugin-basic/plugin-basic.js?hacstag=1296267100"
        in caplog.text
    )
