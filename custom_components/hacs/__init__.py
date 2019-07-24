"""
Custom element manager for community created elements.

For more details about this integration, please refer to the documentation at
https://custom-components.github.io/hacs/
"""
# pylint: disable=bad-continuation
import os.path
import json
from distutils.version import LooseVersion
import aiohttp

import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_START, __version__ as HAVERSION
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

from integrationhelper import Logger, Version
from .aiogithub import AIOGitHub
from .aiogithub.exceptions import (
    AIOGitHubAuthentication,
    AIOGitHubException,
    AIOGitHubRatelimit,
)
from . import const
from .api import HacsAPI, HacsRunningTask
from .http import HacsWebResponse, HacsPluginView, HacsPlugin
from .hacsbase import const as hacsconst, Hacs
from .hacsbase.data import HacsData
from .hacsbase.migration import HacsMigration
from .hacsbase.configuration import Configuration

CONFIG_SCHEMA = vol.Schema(
    {
        const.DOMAIN: vol.Schema(
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
    Hacs.hass = hass
    Hacs.configuration = Configuration(config[const.DOMAIN])
    startup_result = await hacs_startup(Hacs)
    return startup_result


async def hacs_startup(hacs):
    """HACS startup tasks."""
    hacs.logger = Logger("hacs")
    hacs.version = const.VERSION
    hacs.logger.info(const.STARTUP)
    hacs.system.config_path = hacs.hass.config.path()
    hacs.system.ha_version = HAVERSION
    hacs.github = AIOGitHub(
        hacs.configuration.token, async_create_clientsession(hacs.hass)
    )
    hacs.migration = HacsMigration()
    hacs.data = HacsData(Hacs.system.config_path)

    # Check minimum version
    if not check_version(hacs):
        return False

    # Load HACS
    if not await load_hacs_repository(hacs):
        return False

    # Check custom_updater
    if not check_custom_updater(hacs):
        return False

    # Add aditional categories
    if hacs.configuration.appdaemon:
        const.ELEMENT_TYPES.append("appdaemon")
    if hacs.configuration.python_script:
        const.ELEMENT_TYPES.append("python_script")
    if hacs.configuration.theme:
        const.ELEMENT_TYPES.append("theme")
    hacs.common.categories = sorted(const.ELEMENT_TYPES)

    # Print DEV warning
    if hacs.configuration.dev:
        hacs.logger.error(const.DEV_MODE)
        hacs.hass.components.persistent_notification.create(
            title="HACS DEV MODE",
            message=const.DEV_MODE,
            notification_id="hacs_dev_mode",
        )
        # await test_repositories(hacs)

    # Add sensor
    hacs.hass.async_create_task(
        discovery.async_load_platform(
            hacs.hass, "sensor", const.DOMAIN, {}, hacs.configuration.config
        )
    )

    # Set up frontend
    await setup_frontend(hacs)

    # Set up services
    await add_services(hacs)

    return True

    # Setup startup tasks
    hacs.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, hacs.startup_tasks())

    # Mischief managed!
    return True


def check_version(hacs):
    """Check if the version is valid."""
    with open(
        f"{hacs.system.config_path}/custom_components/hacs/manifest.json", "r"
    ) as read:
        manifest = json.loads(read.read())

    # Check if HA is the required version.
    if LooseVersion(hacs.system.ha_version) < LooseVersion(manifest["homeassistant"]):
        hacs.logegr.critical(
            f"You need HA version {manifest['homeassistant']} or newer to use this integration."
        )
        return False
    return True


async def load_hacs_repository(hacs):
    """Load HACS repositroy."""
    try:
        await hacs().register_repository("custom-components/hacs", "integration")
    except (
        AIOGitHubException,
        AIOGitHubRatelimit,
        AIOGitHubAuthentication,
    ) as exception:
        hacs.logger.critical(f"[{exception}] - Could not load HACS!")
        return False
    return True


def check_custom_updater(hacs):
    """Check if custom_updater exist."""
    for location in const.CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(hacs.system.config_path)):
            msg = const.CUSTOM_UPDATER_WARNING.format(
                location.format(hacs.system.config_path)
            )
            hacs.logger.critical(msg)
            return False
    return True


async def setup_frontend(hacs):
    """Configure the HACS frontend elements."""
    # Define views
    hacs.hass.http.register_view(HacsAPI())
    hacs.hass.http.register_view(HacsPlugin())
    hacs.hass.http.register_view(HacsPluginView())
    hacs.hass.http.register_view(HacsRunningTask())
    hacs.hass.http.register_view(HacsWebResponse())

    # Add to sidepanel
    hacs.hass.components.frontend.async_register_built_in_panel(
        "iframe",
        hacs.configuration.sidepanel_title,
        hacs.configuration.sidepanel_icon,
        hacs.configuration.sidepanel_title.lower().replace(" ", "_").replace("-", "_"),
        {"url": hacs.hacsweb + "/overview"},
        require_admin=True,
    )


async def add_services(hacs):
    """Add services."""
    # Service registration
    async def service_hacs_install(call):
        """Install a repository."""
        repository = str(call.data["repository"])
        if repository not in hacs().store.repositories:
            hacs.logger.error("%s is not a konwn repository!", repository)
            return
        repository = hacs().store.repositories[repository]
        await repository.install()

    async def service_hacs_register(call):
        """register a repository."""
        repository = call.data["repository"]
        repository_type = call.data["repository_type"]
        if await hacs().is_known_repository(repository):
            hacs.logger.error("%s is already a konwn repository!", repository)
            return
        await hacs().register_new_repository(repository_type, repository)

    hacs.hass.services.async_register("hacs", "install", service_hacs_install)
    hacs.hass.services.async_register("hacs", "register", service_hacs_register)


async def test_repositories(hacs):
    """Test repositories."""
    await hacs().register_repository("ludeeus/theme-hacs", "theme")
    await hacs().register_repository("ludeeus/ps-hacs", "python_script")
    await hacs().register_repository("ludeeus/integration-hacs", "integration")
    await hacs().register_repository(
        "rgruebel/ha_zigbee2mqtt_networkmap", "integration"
    )
    await hacs().register_repository("ludeeus/ad-hacs", "appdaemon")
    await hacs().register_repository("jonkristian/entur-card", "plugin")  # Dist
    await hacs().register_repository("kalkih/mini-media-player", "plugin")  # Release
    await hacs().register_repository("custom-cards/monster-card", "plugin")  # root
    for repo in hacs.repositories:
        await repo.install()
