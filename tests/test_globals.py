"""Test globals."""
# pylint: disable=missing-docstring
from custom_components.hacs.globals import get_hacs


def test_global_hacs():
    hacs = get_hacs()
    assert hacs.system.lovelace_mode == "storage"
    hacs.system.lovelace_mode = "yaml"
    hacs = get_hacs()
    assert hacs.system.lovelace_mode == "yaml"

