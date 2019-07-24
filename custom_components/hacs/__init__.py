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
from distutils.version import LooseVersion
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
    IFRAME,
    DOMAIN,
)

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
    from .aiogithub.exceptions import (
        AIOGitHubAuthentication,
        AIOGitHubException,
        AIOGitHubRatelimit,
    )
    from .hacsbase import HacsBase as hacs
    from .hacsbase import Hacs
    from .hacsbase.configuration import Configuration

    _LOGGER.info(STARTUP)
    Hacs.configuration = Configuration(config[DOMAIN])
    Hacs.system.config_path = hass.config.path()
    Hacs.system.ha_version = HAVERSION

    # Load manifest
    with open(
        f"{Hacs.system.config_path}/custom_components/hacs/manifest.json", "r"
    ) as read:
        manifest = json.loads(read.read())

    # Check if HA is the required version.
    if LooseVersion(Hacs.system.ha_version) < LooseVersion(manifest["homeassistant"]):
        _LOGGER.critical(
            "You need HA version %s or newer to use this integration.",
            manifest["homeassistant"],
        )
        return False

    # Configure HACS
    try:
        await configure_hacs(hass)
    except AIOGitHubAuthentication as exception:
        _LOGGER.error(exception)
        return False
    except AIOGitHubRatelimit as exception:
        _LOGGER.warning(exception)
    except AIOGitHubException as exception:
        _LOGGER.warning(exception)

    # Check if custom_updater exists
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(Hacs.system.config_path)):
            msg = CUSTOM_UPDATER_WARNING.format(
                location.format(Hacs.system.config_path)
            )
            _LOGGER.critical(msg)
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

    hass.services.async_register("hacs", "install", service_hacs_install)
    hass.services.async_register("hacs", "register", service_hacs_register)

    # Mischief managed!
    return True


async def configure_hacs(hass):
    """Configure HACS."""
    from .aiogithub import AIOGitHub
    from .hacsbase import HacsBase as hacs, Hacs
    from .hacsbase.data import HacsData
    from .hacsbase.developer import Developer
    from . import const
    from .hacsbase import const as hacsconst
    from .hacsbase.migration import HacsMigration

    hacs.config = Hacs.configuration

    if hacs.config.appdaemon:
        ELEMENT_TYPES.append("appdaemon")
    if hacs.config.python_script:
        ELEMENT_TYPES.append("python_script")
    if hacs.config.theme:
        ELEMENT_TYPES.append("theme")

    # Print DEV warning
    if hacs.config.dev:
        _LOGGER.error(const.DEV_MODE)
        hass.components.persistent_notification.create(
            title="HACS DEV MODE",
            message=const.DEV_MODE,
            notification_id="hacs_dev_mode",
        )

    ######################################################################
    ### NEW SETUP ####
    ######################################################################

    Hacs.hass = hass
    Hacs.developer = Developer()
    Hacs.github = AIOGitHub(Hacs.configuration.token, async_create_clientsession(hass))
    Hacs.migration = HacsMigration()
    Hacs.data = HacsData(Hacs.system.config_path)

    # TEST NEW SETUP
    # await Hacs().register_repository("ludeeus/theme-hacs", "theme")
    # await Hacs().register_repository("ludeeus/ps-hacs", "python_script")
    # await Hacs().register_repository("ludeeus/integration-hacs", "integration")
    # await Hacs().register_repository("ludeeus/ad-hacs", "appdaemon")
    await Hacs().register_repository("jonkristian/entur-card", "plugin")  # Dist
    await Hacs().register_repository("kalkih/mini-media-player", "plugin")  # Release
    await Hacs().register_repository("custom-cards/monster-card", "plugin")  # root
    for repo in Hacs.repositories:
        await repo.install()

    ######################################################################
    ### OLD ###
    ######################################################################

    hacs.migration = Hacs.migration

    hacs.aiogithub = Hacs.github
    hacs.hacs_github = await hacs.aiogithub.get_repo("custom-components/hacs")

    hacs.hass = hass
    hacs.const = const
    hacs.hacsconst = hacsconst
    hacs.config_dir = Hacs.system.config_path
    hacs.store = HacsData(Hacs.system.config_path)
    hacs.store.restore_values()
    hacs.element_types = sorted(ELEMENT_TYPES)

    if hacs.config.dev:
        hacs.logger.prefix += ".dev"


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
    hass.components.frontend.async_register_built_in_panel(
        "iframe",
        hacs.config.sidepanel_title,
        hacs.config.sidepanel_icon,
        hacs.config.sidepanel_title.lower().replace(" ", "_").replace("-", "_"),
        {"url": hacs.hacsweb + "/overview"},
        require_admin=IFRAME["require_admin"],
    )
