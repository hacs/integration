"""HACS Sensor Test Suite."""
# pylint: disable=missing-docstring
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories import HacsIntegrationRepository
from custom_components.hacs.sensor import (
    HACSSensor,
    async_setup_entry,
    async_setup_platform,
)


async def sensor_setup(hacs: HacsBase, hass: HomeAssistant) -> HACSSensor:
    """Set up the sensor."""
    sensor = HACSSensor(hacs)
    sensor.hass = hass
    sensor.entity_id = "sensor.hacs"

    await sensor.async_added_to_hass()
    return sensor


def mock_setup(entities):
    for entity in entities:
        assert entity.name == "hacs"


@pytest.mark.asyncio
async def test_sensor_data(hacs: HacsBase, hass: HomeAssistant):
    sensor = await sensor_setup(hacs, hass)
    assert sensor.name == "hacs"
    assert sensor.icon == "hacs:hacs"
    assert sensor.unique_id.startswith("0717a0cd")
    assert sensor.unit_of_measurement == "pending update(s)"


@pytest.mark.asyncio
async def test_device_info_entry_type_pre_2021_12(hacs: HacsBase, hass: HomeAssistant):
    # LEGACY can be removed when min HA version is 2021.12
    hacs.core.ha_version = "2021.12.0"
    sensor = await sensor_setup(hacs, hass)
    entry_type = sensor.device_info["entry_type"]
    assert entry_type == "service"
    assert isinstance(entry_type, str)


@pytest.mark.asyncio
async def test_device_info_entry_type(hacs: HacsBase, hass: HomeAssistant):
    sensor = await sensor_setup(hacs, hass)
    entry_type = sensor.device_info["entry_type"]
    assert entry_type == DeviceEntryType.SERVICE
    assert isinstance(entry_type, DeviceEntryType)


@pytest.mark.asyncio
async def test_sensor_update_event(hacs: HacsBase, hass: HomeAssistant):
    sensor = await sensor_setup(hacs, hass)

    repository = HacsIntegrationRepository(hacs, "test/one")
    repository.data.update_data(
        {
            "id": "123",
            "installed": True,
            "installed_version": "1",
            "last_version": "2",
        }
    )
    hacs.repositories.register(repository)

    repository = HacsIntegrationRepository(hacs, "test/two")
    repository.data.update_data(
        {
            "id": "321",
            "installed": True,
            "installed_version": "1",
            "last_version": "1",
        }
    )
    hacs.repositories.register(repository)

    hacs.common.categories = {"integration"}
    assert sensor.state is None

    hass.bus.async_fire("hacs/status", {})

    await hass.async_block_till_done()
    assert sensor.state == 1


@pytest.mark.asyncio
async def test_sensor_update_event_background_task(hacs: HacsBase, hass: HomeAssistant):
    sensor = await sensor_setup(hacs, hass)

    repository = HacsIntegrationRepository(hacs, "test/one")
    repository.data.update_data(
        {
            "id": "123",
            "installed": True,
            "installed_version": "1",
            "last_version": "2",
        }
    )
    hacs.repositories.register(repository)

    repository = HacsIntegrationRepository(hacs, "test/two")
    repository.data.update_data(
        {
            "id": "321",
            "installed": True,
            "installed_version": "1",
            "last_version": "1",
        }
    )
    hacs.repositories.register(repository)

    hacs.common.categories = {"integration"}
    assert sensor.state is None
    hacs.status.background_task = True

    hass.bus.async_fire("hacs/status", {})

    await hass.async_block_till_done()
    assert sensor.state is None


@pytest.mark.asyncio
async def test_sensor_update_manual(hacs: HacsBase, hass: HomeAssistant):
    sensor = await sensor_setup(hacs, hass)

    repository = HacsIntegrationRepository(hacs, "test/one")
    repository.data.update_data(
        {
            "id": "123",
            "installed": True,
            "installed_version": "1",
            "last_version": "2",
        }
    )
    hacs.repositories.register(repository)

    repository = HacsIntegrationRepository(hacs, "test/two")
    repository.data.update_data(
        {
            "id": "321",
            "installed": True,
            "installed_version": "1",
            "last_version": "1",
        }
    )
    hacs.repositories.register(repository)

    hacs.common.categories = {"integration"}
    assert sensor.state is None

    await sensor.async_update()
    assert sensor.state == 1


@pytest.mark.asyncio
async def test_setup_platform(hass: HomeAssistant):
    await async_setup_platform(hass, {}, mock_setup)


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant):
    await async_setup_entry(hass, {}, mock_setup)
