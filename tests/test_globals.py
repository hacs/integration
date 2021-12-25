"""Test globals."""
# pylint: disable=missing-docstring


def test_global_hacs(hacs):
    assert hacs.core.lovelace_mode == "yaml"
    hacs.core.lovelace_mode = "storage"
    assert hacs.core.lovelace_mode == "storage"
