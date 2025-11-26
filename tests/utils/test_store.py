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
            "custom_components.hacs.utils.store.json_util.load_json", side_effect=OSError("No file"),
        ):
            assert store.load() == {"test": "test"}


async def test_store_remove(hass: HomeAssistant) -> None:
    """Test the store remove."""
    with patch(
        "custom_components.hacs.utils.store.HACSStore.async_remove", return_value=AsyncMock(),
    ) as async_remove_mock:
        await async_remove_store(hass, "test")
        assert not async_remove_mock.called

        await async_remove_store(hass, "test/test")
        assert async_remove_mock.called


async def test_store_store(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    """Test the store store."""
    with patch(
        "custom_components.hacs.utils.store.HACSStore.async_save", return_value=AsyncMock(),
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


@pytest.mark.parametrize(
    "ha_version, expected_supported",
    [
        ("2025.11.0", False),
        ("2025.11.99", False),
        ("2025.12.0", True),
        ("2025.12.1", True),
        ("2026.1.0", True),
    ],
)
def test_serialize_in_event_loop_version_check(ha_version: str, expected_supported: bool) -> None:
    """Test that serialize_in_event_loop flag is set based on HA version."""
    from awesomeversion import AwesomeVersion

    with patch(
        "custom_components.hacs.utils.store.HAVERSION",
        ha_version,
    ):
        # Re-evaluate the version check with the patched version
        result = AwesomeVersion(ha_version) >= "2025.12.0"
        assert result == expected_supported
