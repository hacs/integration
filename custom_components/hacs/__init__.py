"""
Custom element manager for community created elements.

For more details about this component, please refer to the documentation at
https://custom-components.github.io/hacs/
"""
import logging
import os.path
import json
import asyncio
from datetime import datetime, timedelta
from pkg_resources import parse_version
import aiohttp

import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_START, __version__ as HAVERSION
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

from .hacsbase import HacsBase as hacs
from .const import (
    CUSTOM_UPDATER_LOCATIONS,
    STARTUP,
    ISSUE_URL,
    CUSTOM_UPDATER_WARNING,
    NAME_LONG,
    NAME_SHORT,
    DOMAIN_DATA,
    ELEMENT_TYPES,
    VERSION,
    IFRAME,
    BLACKLIST,
)

from .frontend.views import (
    HacsStaticView,
    HacsErrorView,
    HacsPluginView,
    HacsOverviewView,
    HacsStoreView,
    HacsSettingsView,
    HacsRepositoryView,
    HacsAPIView,
)

DOMAIN = "{}".format(NAME_SHORT.lower())

# TODO: Remove this when minimum HA version is > 0.93
REQUIREMENTS = ["aiofiles", "backoff"]

_LOGGER = logging.getLogger("custom_components.hacs")

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("token"): cv.string,
                vol.Optional("appdaemon", default=False): cv.boolean,
                vol.Optional("python_script", default=False): cv.boolean,
                vol.Optional("theme", default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):  # pylint: disable=unused-argument
    """Set up this component."""
    _LOGGER.info(STARTUP)
    config_dir = hass.config.path()
    github_token = config[DOMAIN]["token"]

    if config[DOMAIN]["appdaemon"]:
        ELEMENT_TYPES.append("appdaemon")
    if config[DOMAIN]["python_script"]:
        ELEMENT_TYPES.append("python_script")
    if config[DOMAIN]["theme"]:
        ELEMENT_TYPES.append("theme")

    # Print DEV warning
    if VERSION == "DEV":
        _LOGGER.error(
            "You are running a DEV version of HACS, this is not intended for regular use."
        )

    # Configure HACS
    await configure_hacs(hass, github_token, config_dir)

    # Check if custom_updater exists
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(config_dir)):
            msg = CUSTOM_UPDATER_WARNING.format(location.format(config_dir))
            _LOGGER.critical(msg)
            return False

    # Check if HA is the required version.
    if parse_version(HAVERSION) < parse_version("0.92.0"):
        _LOGGER.critical("You need HA version 92 or newer to use this integration.")
        return False

    # Add sensor
    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config[DOMAIN])
    )

    # Setup startup tasks
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, hacs().startup_tasks())

    # Register the views
    hass.http.register_view(HacsStaticView())
    hass.http.register_view(HacsErrorView())
    hass.http.register_view(HacsPluginView())
    hass.http.register_view(HacsStoreView())
    hass.http.register_view(HacsOverviewView())
    hass.http.register_view(HacsSettingsView())
    hass.http.register_view(HacsRepositoryView())
    hass.http.register_view(HacsAPIView())

    # Add to sidepanel
    # TODO: Remove this check when minimum HA version is > 0.94
    if parse_version(HAVERSION) < parse_version("0.93.9"):
        await hass.components.frontend.async_register_built_in_panel(
            "iframe",
            IFRAME["title"],
            IFRAME["icon"],
            IFRAME["path"],
            {"url": hacs.url_path["overview"]},
            require_admin=IFRAME["require_admin"],
        )
    else:
        hass.components.frontend.async_register_built_in_panel(
            "iframe",
            IFRAME["title"],
            IFRAME["icon"],
            IFRAME["path"],
            {"url": hacs.url_path["overview"]},
            require_admin=IFRAME["require_admin"],
        )

    # Mischief managed!
    return True


async def configure_hacs(hass, github_token, hass_config_dir):
    """Configure HACS."""
    from .aiogithub import AIOGitHub
    from .hacsmigration import HacsMigration
    from .hacsstorage import HacsStorage

    hacs.migration = HacsMigration()
    hacs.storage = HacsStorage()

    hacs.aiogithub = AIOGitHub(
        github_token, hass.loop, async_create_clientsession(hass)
    )

    hacs.hass = hass
    hacs.config_dir = hass_config_dir
    hacs.blacklist = BLACKLIST
