"""Test network."""
from custom_components.hacs.helpers.network import internet_connectivity_check


def test_networl():
    assert internet_connectivity_check()
