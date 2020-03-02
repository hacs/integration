"""Test network."""
# pylint: disable=missing-docstring,invalid-name
from custom_components.hacs.helpers.network import internet_connectivity_check


def test_network():
    assert internet_connectivity_check()


def test_network_issues():
    assert not internet_connectivity_check("None")
