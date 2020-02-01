"""HACS Sensor Test Suite."""
# pylint: disable=missing-docstring
import pytest
from custom_components.hacs.sensor import HACSSensor


def test_sensor_data():
    sensor = HACSSensor()
    assert sensor.name == "hacs"
    assert sensor.device_state_attributes


@pytest.mark.asyncio
async def test_sensor_update():
    sensor = HACSSensor()
    dummy_state = "DUMMY"
    sensor._state = dummy_state  # pylint: disable=protected-access
    assert sensor.state == dummy_state
    await sensor.async_update()
    assert sensor.state == 0
