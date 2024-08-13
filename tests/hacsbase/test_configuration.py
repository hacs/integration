"""HacsConfiguration Test Suite."""
# pylint: disable=missing-docstring
import pytest

from custom_components.hacs.base import HacsConfiguration
from custom_components.hacs.exceptions import HacsException


def test_configuration_and_option():
    config = HacsConfiguration()
    config.update_from_dict({"token": "xxxxxxxxxx"})

    assert isinstance(config.to_json(), dict)

    assert isinstance(config.token, str)
    assert config.token == "xxxxxxxxxx"

    assert isinstance(config.sidepanel_title, str)
    assert config.sidepanel_title == "HACS"

    assert isinstance(config.sidepanel_icon, str)
    assert config.sidepanel_icon == "hacs:hacs"

    assert isinstance(config.appdaemon, bool)
    assert not config.appdaemon

    assert isinstance(config.python_script, bool)
    assert not config.python_script

    assert isinstance(config.theme, bool)
    assert not config.theme

    assert isinstance(config.country, str)
    assert config.country == "ALL"

    assert isinstance(config.release_limit, int)
    assert config.release_limit == 5


def test_ignore_experimental():
    """Test experimental setting is ignored."""
    config = HacsConfiguration()
    assert not hasattr(config, "experimental")

    config.update_from_dict({"experimental": False})
    assert not hasattr(config, "experimental")


def test_ignore_netdaemon():
    """Test netdaemon setting is ignored."""
    config = HacsConfiguration()
    assert not hasattr(config, "netdaemon")

    config.update_from_dict({"netdaemon": True})
    assert not hasattr(config, "netdaemon")


def test_edge_update_with_none():
    config = HacsConfiguration()
    with pytest.raises(HacsException):
        assert config.update_from_dict(None)
