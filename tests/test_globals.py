"""Test globals."""
# pylint: disable=missing-docstring
from custom_components.hacs.globals import get_hacs, get_hass


def test_global_hacs():
    hacs = get_hacs()
    assert hacs.system.lovelace_mode == "storage"
    hacs.system.lovelace_mode = "yaml"
    hacs = get_hacs()
    assert hacs.system.lovelace_mode == "yaml"


def test_global_hass():
    hass = get_hass()
    assert not hass

    hacs = get_hacs()
    hacs.hass = True
    hass = get_hass()
    assert hass
