"""
Custom element manager for community created elements.

For more details about this integration, please refer to the documentation at
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
    DOMAIN,
)


# TODO: Remove this when minimum HA version is > 0.93
REQUIREMENTS = ["aiofiles==0.4.0", "backoff==1.8.0", "packaging==19.0"]

_LOGGER = logging.getLogger("custom_components.hacs")

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("token"): cv.string,
                vol.Optional("sidepanel_title"): cv.string,
                vol.Optional("sidepanel_icon"): cv.string,
                vol.Optional("dev", default=False): cv.boolean,
                vol.Optional("appdaemon", default=False): cv.boolean,
                vol.Optional("python_script", default=False): cv.boolean,
                vol.Optional("theme", default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):  # pylint: disable=unused-argument
    """Set up this integration."""
    from .aiogithub.exceptions import AIOGitHubAuthentication, AIOGitHubException, AIOGitHubRatelimit
    from .hacsbase import HacsBase as hacs

    _LOGGER.info(STARTUP)
    config_dir = hass.config.path()

    # Configure HACS
    try:
        await configure_hacs(hass, config[DOMAIN], config_dir)
    except AIOGitHubAuthentication as exception:
        _LOGGER.error(exception)
        return False
    except AIOGitHubRatelimit as exception:
        _LOGGER.warning(exception)
    except AIOGitHubException as exception:
        _LOGGER.warning(exception)

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

    await setup_frontend(hass, hacs)

    # Service registration
    async def service_hacs_install(call):
        """Install a repository."""
        repository = str(call.data["repository"])
        if repository not in hacs().store.repositories:
            _LOGGER.error("%s is not a konwn repository!", repository)
            return
        repository = hacs().store.repositories[repository]
        await repository.install()

    async def service_hacs_register(call):
        """register a repository."""
        repository = call.data["repository"]
        repository_type = call.data["repository_type"]
        if await hacs().is_known_repository(repository):
            _LOGGER.error("%s is already a konwn repository!", repository)
            return
        await hacs().register_new_repository(repository_type, repository)

    hass.services.async_register("hacs", 'install', service_hacs_install)
    hass.services.async_register("hacs", 'register', service_hacs_register)

    # Mischief managed!
    return True


async def configure_hacs(hass, configuration, hass_config_dir):
    """Configure HACS."""
    from .aiogithub import AIOGitHub
    from .hacsbase import HacsBase as hacs
    from .hacsbase.configuration import HacsConfiguration
    from .hacsbase.data import HacsData
    from . import const as const
    from .hacsbase import const as hacsconst
    from .hacsbase.migration import HacsMigration
    #from .hacsbase.storage import HacsStorage

    hacs.config = HacsConfiguration(configuration)

    if hacs.config.appdaemon:
        ELEMENT_TYPES.append("appdaemon")
    if hacs.config.python_script:
        ELEMENT_TYPES.append("python_script")
    if hacs.config.theme:
        ELEMENT_TYPES.append("theme")

    # Print DEV warning
    if hacs.config.dev:
        _LOGGER.error(
            const.DEV_MODE
        )
        hass.components.persistent_notification.create(
            title="HACS DEV MODE",
            message=const.DEV_MODE,
            notification_id="hacs_dev_mode"
        )

    hacs.migration = HacsMigration()
    #hacs.storage = HacsStorage()

    hacs.aiogithub = AIOGitHub(
        hacs.config.token, hass.loop, async_create_clientsession(hass)
    )

    hacs.hacs_github = await hacs.aiogithub.get_repo("custom-components/hacs")

    hacs.hass = hass
    hacs.const = const
    hacs.hacsconst = hacsconst
    hacs.config_dir = hass_config_dir
    hacs.store = HacsData(hass_config_dir)
    hacs.store.restore_values()
    hacs.element_types = sorted(ELEMENT_TYPES)


async def setup_frontend(hass, hacs):
    """Configure the HACS frontend elements."""
    from .api import HacsAPI, HacsRunningTask
    from .http import HacsWebResponse, HacsPluginView, HacsPlugin

    # Define views
    hass.http.register_view(HacsAPI())
    hass.http.register_view(HacsPlugin())
    hass.http.register_view(HacsPluginView())
    hass.http.register_view(HacsRunningTask())
    hass.http.register_view(HacsWebResponse())

    # Add to sidepanel
    # TODO: Remove this check when minimum HA version is > 0.94
    if parse_version(HAVERSION) < parse_version("0.93.9"):
        await hass.components.frontend.async_register_built_in_panel(
            "iframe",
            hacs.config.sidepanel_title,
            hacs.config.sidepanel_icon,
            hacs.config.sidepanel_title.lower().replace(" ", "_").replace("-", "_"),
            {"url": hacs.hacsweb + "/overview"},
            require_admin=IFRAME["require_admin"],
        )
    else:
        hass.components.frontend.async_register_built_in_panel(
            "iframe",
            hacs.config.sidepanel_title,
            hacs.config.sidepanel_icon,
            hacs.config.sidepanel_title.lower().replace(" ", "_").replace("-", "_"),
            {"url": hacs.hacsweb + "/overview"},
            require_admin=IFRAME["require_admin"],
        )
