"""Test network."""
# pylint: disable=missing-docstring,invalid-name

import pytest
from custom_components.hacs.helpers.network import internet_connectivity_check


def test_network():
    assert internet_connectivity_check()


@pytest.mark.allow_hosts(["127.0.0.1"])
def test_network_issues():
    assert not internet_connectivity_check()
