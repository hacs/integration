"""HACS configuration schema Test Suite."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.configuration_schema import (
    hacs_config_combined,
)


def test_combined():
    assert isinstance(hacs_config_combined(), dict)
