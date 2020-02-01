"""HACS Sensor Test Suite."""
# pylint: disable=missing-docstring
import pytest
from custom_components.hacs.sensor import HACSSensor

SENSOR = HACSSensor()


def test_sensor_data():
    assert SENSOR.name == "hacs"
    assert SENSOR.device_state_attributes


@pytest.mark.asyncio
async def test_sensor_update():
    dummy_state = "DUMMY"
    SENSOR._state = dummy_state  # pylint: disable=protected-access
    assert SENSOR.state == dummy_state
    await SENSOR.async_update()
    assert SENSOR.state == 0
