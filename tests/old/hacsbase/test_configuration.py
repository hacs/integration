"""Configuration Test Suite."""
# pylint: disable=missing-docstring
import pytest

from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.helpers.classes.exceptions import HacsException


def test_configuration_and_option():
    config = Configuration.from_dict({"token": "xxxxxxxxxx"}, {})

    assert isinstance(config.to_json(), dict)
    config.print()

    assert isinstance(config.options, dict)
    assert isinstance(config.config, dict)

    assert isinstance(config.token, str)
    assert config.token == "xxxxxxxxxx"

    assert isinstance(config.sidepanel_title, str)
    assert config.sidepanel_title == "HACS"

    assert isinstance(config.sidepanel_icon, str)
    assert config.sidepanel_icon == "hacs:hacs"

    assert isinstance(config.appdaemon, bool)
    assert not config.appdaemon

    assert isinstance(config.netdaemon, bool)
    assert not config.netdaemon

    assert isinstance(config.python_script, bool)
    assert not config.python_script

    assert isinstance(config.onboarding_done, bool)
    assert not config.onboarding_done

    assert isinstance(config.theme, bool)
    assert not config.theme

    assert isinstance(config.options, dict)

    assert isinstance(config.country, str)
    assert config.country == "ALL"

    assert isinstance(config.release_limit, int)
    assert config.release_limit == 5

    assert isinstance(config.experimental, bool)
    assert not config.experimental


def test_edge_option_only_pass_empty_dict_as_configuration():
    with pytest.raises(HacsException):
        assert Configuration.from_dict({}, {"experimental": True})


def test_edge_configuration_only_pass_none_as_option():
    assert Configuration.from_dict({"token": "xxxxxxxxxx"}, None)


def test_edge_options_true():
    with pytest.raises(HacsException):
        assert Configuration.from_dict({"options": True}, None)
