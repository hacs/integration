"""Tests for async_remove_config_entry_device function.

This file contains comprehensive tests for the async_remove_config_entry_device function
in the HACS integration. These tests cover all the main code paths and edge cases.
"""

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry
import pytest

from custom_components.hacs import async_remove_config_entry_device
from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN, HACS_SYSTEM_ID


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_success(hass: HomeAssistant, hacs: HacsBase):
    """Test successful device removal."""
    hacs.repositories.is_downloaded = MagicMock(return_value=False)
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with proper HACS identifier
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {(DOMAIN, "123456")}

    # Test successful removal
    result = await async_remove_config_entry_device(hass, config_entry, device_entry)

    assert result is True
    hacs.repositories.is_downloaded.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_no_identifier(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal fails when no valid HACS identifier is found."""
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry without HACS identifier
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {
        ("other_domain", "123456"), ("another_domain", "789")}

    # Test that it raises HomeAssistantError
    with pytest.raises(HomeAssistantError, match="Cannot remove service test_device_id, no valid HACS repository identifier found"):
        await async_remove_config_entry_device(hass, config_entry, device_entry)


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_hacs_system_id(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal fails when trying to remove HACS system device."""
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with HACS system identifier
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {(DOMAIN, HACS_SYSTEM_ID)}

    # Test that it raises HomeAssistantError
    with pytest.raises(HomeAssistantError, match="Cannot remove the service for HACS itself"):
        await async_remove_config_entry_device(hass, config_entry, device_entry)


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_still_downloaded(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal fails when repository is still downloaded."""
    # Create a mock repository
    mock_repository = MagicMock()
    mock_repository.data.full_name = "test/repository"

    # Mock the repository being downloaded
    hacs.repositories.is_downloaded = MagicMock(return_value=True)
    hacs.repositories.get_by_id = MagicMock(return_value=mock_repository)
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with proper HACS identifier
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {(DOMAIN, "123456")}

    # Test that it raises HomeAssistantError
    with pytest.raises(HomeAssistantError, match="Cannot remove service for test/repository, it is still downloaded in HACS"):
        await async_remove_config_entry_device(hass, config_entry, device_entry)

    hacs.repositories.is_downloaded.assert_called_once_with("123456")
    hacs.repositories.get_by_id.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_empty_identifiers(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal fails when device has no identifiers."""
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with empty identifiers
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = set()

    # Test that it raises HomeAssistantError
    with pytest.raises(HomeAssistantError, match="Cannot remove service test_device_id, no valid HACS repository identifier found"):
        await async_remove_config_entry_device(hass, config_entry, device_entry)


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_invalid_identifier_format(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal fails when HACS identifier has invalid format."""
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with invalid HACS identifier format
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {
        (DOMAIN,),  # Tuple with only one element
        (DOMAIN, "123", "extra"),  # Tuple with too many elements
        "invalid_string",  # Not a tuple
    }

    # Test that it raises HomeAssistantError
    with pytest.raises(HomeAssistantError, match="Cannot remove service test_device_id, no valid HACS repository identifier found"):
        await async_remove_config_entry_device(hass, config_entry, device_entry)


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_multiple_identifiers(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal succeeds when device has multiple identifiers including a valid HACS one."""
    hacs.repositories.is_downloaded = MagicMock(return_value=False)
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with multiple identifiers, including a valid HACS one
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {
        ("other_domain", "other_id"),
        (DOMAIN, "123456"),  # Valid HACS identifier
        ("another_domain", "another_id"),
    }

    # Test successful removal
    result = await async_remove_config_entry_device(hass, config_entry, device_entry)

    assert result is True
    hacs.repositories.is_downloaded.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_with_integer_id(hass: HomeAssistant, hacs: HacsBase):
    """Test device removal works with integer repository ID."""
    hacs.repositories.is_downloaded = MagicMock(return_value=False)
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with integer repository ID
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {(DOMAIN, 123456)}  # Integer ID

    # Test successful removal
    result = await async_remove_config_entry_device(hass, config_entry, device_entry)

    assert result is True
    hacs.repositories.is_downloaded.assert_called_once_with(123456)


@pytest.mark.asyncio
async def test_async_remove_config_entry_device_system_id_with_multiple_identifiers(hass: HomeAssistant, hacs: HacsBase):
    """Test that HACS system ID is detected even with multiple identifiers."""
    config_entry = MagicMock(spec=ConfigEntry)

    # Create device entry with multiple identifiers, including HACS system ID
    device_entry = MagicMock(spec=DeviceEntry)
    device_entry.id = "test_device_id"
    device_entry.identifiers = {
        ("other_domain", "other_id"),
        (DOMAIN, HACS_SYSTEM_ID),  # HACS system ID
        ("another_domain", "another_id"),
    }

    # Test that it raises HomeAssistantError for HACS system ID
    with pytest.raises(HomeAssistantError, match="Cannot remove the service for HACS itself"):
        await async_remove_config_entry_device(hass, config_entry, device_entry)
