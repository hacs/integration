"""Data Test Suite."""
import pytest
from tests.async_mock import patch
from custom_components.hacs.hacsbase.data import HacsData


@pytest.mark.asyncio
async def test_hacs_data_async_write1(hacs, repository):
    data = HacsData()
    repository.data.installed = True
    repository.data.installed_version = "1"
    hacs.async_set_repositories([repository])
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_async_write2(hacs):
    data = HacsData()
    hacs.status.background_task = False
    hacs.system.disabled = False
    hacs.async_set_repositories([])
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_restore_write_new(hacs):
    data = HacsData()
    await data.restore()
    with patch(
        "custom_components.hacs.hacsbase.data.async_save_to_store"
    ) as mock_async_save_to_store, patch(
        "custom_components.hacs.hacsbase.data.async_save_to_store_default_encoder"
    ) as mock_async_save_to_store_default_encoder:
        await data.async_write()
    assert mock_async_save_to_store.called
    assert not mock_async_save_to_store_default_encoder.called


@pytest.mark.asyncio
async def test_hacs_data_restore_write_not_new(hacs):
    data = HacsData()

    async def _mocked_loads(hass, key):
        if key == "repositories":
            return {
                "172733314": {
                    "authors": ["@ludeeus"],
                    "category": "integration",
                    "description": "HACS gives you a powerful UI to handle downloads of all your custom needs.",
                    "domain": "hacs",
                    "downloads": 2161,
                    "etag_repository": 'W/"35bbcc68e17782aa6a824fd976a6457e8a942f8781e351f41823fe591d13321b"',
                    "full_name": "hacs/integration",
                    "first_install": True,
                    "installed_commit": "7ef48bf",
                    "installed": True,
                    "last_commit": "cc36b54",
                    "last_release_tag": "1.12.3",
                    "last_updated": "2021-04-29T07:12:14Z",
                    "name": "hacs",
                    "new": False,
                    "repository_manifest": {
                        "name": "HACS",
                        "zip_release": True,
                        "hide_default_branch": True,
                        "homeassistant": "2020.12.0",
                        "hacs": "0.19.0",
                        "filename": "hacs.zip",
                    },
                    "selected_tag": None,
                    "show_beta": False,
                    "stars": 1660,
                    "topics": [
                        "community",
                        "hacktoberfest",
                        "hacs",
                        "home-assistant",
                        "integration",
                        "package-manager",
                        "python",
                    ],
                    "version_installed": "1.12.1",
                }
            }
        elif key == "hacs":
            return {"view": "Grid", "compact": False, "onboarding_done": True}
        else:
            raise ValueError(f"No mock for {key}")

    with patch(
        "custom_components.hacs.hacsbase.data.async_load_from_store",
        side_effect=_mocked_loads,
    ):
        await data.restore()

    assert hacs.get_by_id("172733314")
    assert hacs.get_by_name("hacs/integration")

    with patch(
        "custom_components.hacs.hacsbase.data.async_save_to_store"
    ) as mock_async_save_to_store, patch(
        "custom_components.hacs.hacsbase.data.async_save_to_store_default_encoder"
    ) as mock_async_save_to_store_default_encoder:
        await data.async_write()
    assert mock_async_save_to_store.called
    assert mock_async_save_to_store_default_encoder.called
