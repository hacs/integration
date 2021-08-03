"""HACS Sensor Test Suite."""
# pylint: disable=missing-docstring
import pytest

from custom_components.hacs.repositories import HacsIntegrationRepository
from custom_components.hacs.sensor import (
    HACSSensor,
    async_setup_entry,
    async_setup_platform,
)


def mock_setup(entities):  # pylint: disable=unused-argument
    for entity in entities:
        assert entity.name == "hacs"


def test_sensor_data():
    sensor = HACSSensor()
    repository = HacsIntegrationRepository("test/test")
    sensor.repositories = [repository]
    assert sensor.name == "hacs"
    assert sensor.device_state_attributes
    assert sensor.device_info
    assert sensor.icon == "hacs:hacs"
    assert sensor.unique_id.startswith("0717a0cd")
    assert sensor.unit_of_measurement == "pending update(s)"


@pytest.mark.asyncio
async def test_sensor_update(hacs):
    sensor = HACSSensor()
    repository = HacsIntegrationRepository("test/one")
    repository.data.installed = True
    repository.data.installed_version = "1"
    repository.data.last_version = "2"
    hacs.async_add_repository(repository)
    repository = HacsIntegrationRepository("test/two")
    repository.data.installed = True
    repository.data.installed_version = "1"
    repository.data.last_version = "1"
    hacs.async_add_repository(repository)
    hacs.common.categories = ["integration"]
    dummy_state = "DUMMY"
    sensor._state = dummy_state  # pylint: disable=protected-access
    assert sensor.state == dummy_state
    await sensor.async_update()
    assert sensor.state == 1

    hacs.status.background_task = True
    sensor._state = dummy_state  # pylint: disable=protected-access
    assert sensor.state == dummy_state
    await sensor.async_update()
    assert sensor.state == dummy_state


@pytest.mark.asyncio
async def test_setup_platform(hass):
    await async_setup_platform(hass, {}, mock_setup)


@pytest.mark.asyncio
async def test_setup_entry(hass):
    await async_setup_entry(hass, {}, mock_setup)
