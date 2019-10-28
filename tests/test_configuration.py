"""Configuration Test Suite."""
# pylint: disable=missing-docstring
import pytest
from custom_components.hacs.hacsbase.configuration import Configuration


def test_configuration_and_option():
    config = Configuration.from_dict({"token": "xxxxxxxxxx"}, {})

    assert isinstance(config.options, dict)
    assert isinstance(config.config, dict)

    assert isinstance(config.token, str)
    assert config.token == "xxxxxxxxxx"

    assert isinstance(config.sidepanel_title, str)
    assert config.sidepanel_title == "Community"

    assert isinstance(config.sidepanel_icon, str)
    assert config.sidepanel_icon == "mdi:alpha-c-box"

    assert isinstance(config.appdaemon, bool)
    assert not config.appdaemon

    assert isinstance(config.python_script, bool)
    assert not config.python_script

    assert isinstance(config.theme, bool)
    assert not config.theme

    assert isinstance(config.options, dict)

    assert isinstance(config.country, str)
    assert config.country == "ALL"

    assert isinstance(config.release_limit, int)
    assert config.release_limit == 5

    assert isinstance(config.experimental, bool)
    assert not config.experimental


def test_configuration_only_pass_dict():
    assert Configuration.from_dict({"token": "xxxxxxxxxx"}, {})


def test_option_only_pass_dict():
    assert Configuration.from_dict({}, {"experimental": True})


def test_configuration_only_pass_none():
    assert Configuration.from_dict({"token": "xxxxxxxxxx"}, None)
