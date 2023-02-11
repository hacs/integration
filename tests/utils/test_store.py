"""Queue tests."""
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.const import VERSION_STORAGE
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.utils.store import (
    async_load_from_store,
    async_remove_store,
    async_save_to_store,
    get_store_for_key,
)


@pytest.mark.asyncio
async def test_store_load(hass: HomeAssistant) -> None:
    """Test the store load."""

    store = get_store_for_key(hass, "test")

    with patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={"version": VERSION_STORAGE, "data": {"test": "test"}},
    ):
        assert store.load() == {"test": "test"}
        assert await async_load_from_store(hass, "test") == {"test": "test"}

    with patch("custom_components.hacs.utils.store.json_util.load_json", return_value={}):
        assert store.load() is None

    with pytest.raises(HacsException):
        with patch(
            "custom_components.hacs.utils.store.json_util.load_json", side_effect=OSError("No file")
        ):
            assert store.load() == {"test": "test"}


@pytest.mark.asyncio
async def test_store_remove(hass: HomeAssistant) -> None:
    """Test the store remove."""

    with patch(
        "custom_components.hacs.utils.store.HACSStore.async_remove", return_value=AsyncMock()
    ) as async_remove_mock:
        await async_remove_store(hass, "test")
        assert not async_remove_mock.called

        await async_remove_store(hass, "test/test")
        assert async_remove_mock.called


@pytest.mark.asyncio
async def test_store_store(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    """Test the store store."""

    with patch(
        "custom_components.hacs.utils.store.HACSStore.async_save", return_value=AsyncMock()
    ) as async_save_mock, patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={"version": VERSION_STORAGE, "data": {}},
    ):
        await async_save_to_store(hass, "test", {})
        assert not async_save_mock.called
        assert (
            "<HACSStore async_save_to_store> Did not store data for 'hacs.test'. Content did not change"
            in caplog.text
        )

        await async_save_to_store(hass, "test", {"test": "test"})
        assert async_save_mock.call_count == 1
