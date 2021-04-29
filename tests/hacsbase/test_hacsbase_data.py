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
    assert mock_async_save_to_store_default_encoder.called


@pytest.mark.asyncio
async def test_hacs_data_restore_write_not_new(hacs):
    data = HacsData()

    async def _mocked_loads(hass, key):
        if key == "repositories":
            return {
                "172733314": {
                    "category": "integration",
                    "full_name": "hacs/integration",
                }
            }
        elif key == "hacs":
            return {"view": "Grid", "compact": False, "onboarding_done": True}
        else:
            raise ValueError(f"No mock for {key}")

    def _mocked_load(*_):
        return {
            "category": "integration",
            "full_name": "hacs/integration",
            "show_beta": True,
        }

    with patch("os.path.exists", return_value=True), patch(
        "custom_components.hacs.hacsbase.data.async_load_from_store",
        side_effect=_mocked_loads,
    ), patch(
        "custom_components.hacs.helpers.functions.store.HACSStore.load",
        side_effect=_mocked_load,
    ):
        await data.restore()

    assert hacs.get_by_id("172733314")
    assert hacs.get_by_name("hacs/integration")
    assert hacs.get_by_id("172733314").data.show_beta is True

    with patch(
        "custom_components.hacs.hacsbase.data.async_save_to_store"
    ) as mock_async_save_to_store, patch(
        "custom_components.hacs.hacsbase.data.async_save_to_store_default_encoder"
    ) as mock_async_save_to_store_default_encoder:
        await data.async_write()
    assert mock_async_save_to_store.called
    assert mock_async_save_to_store_default_encoder.called
