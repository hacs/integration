"""
Custom element manager for community created elements.

For more details about this integration, please refer to the documentation at
https://hacs.netlify.com/
"""
# pylint: disable=bad-continuation
from asyncio import sleep
import os.path
import json
from distutils.version import LooseVersion
import aiohttp

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import EVENT_HOMEASSISTANT_START, __version__ as HAVERSION
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery, device_registry as dr
from homeassistant.helpers.event import async_call_later

from aiogithubapi import (
    AIOGitHub,
    AIOGitHubAuthentication,
    AIOGitHubException,
    AIOGitHubRatelimit,
)
from integrationhelper import Logger, Version

from . import const
from .api import HacsAPI, HacsRunningTask
from .http import HacsWebResponse, HacsPluginView, HacsPlugin
from .hacsbase import const as hacsconst, Hacs
from .hacsbase.data import HacsData
from .hacsbase.configuration import Configuration
from .hacsbase.migration import ValidateData


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional("country"): vol.All(cv.string, vol.In(const.LOCALE)),
        vol.Optional("release_limit"): cv.positive_int,
    }
)


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
                vol.Optional("options"): OPTIONS_SCHEMA,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):  # pylint: disable=unused-argument
    """Set up this integration using yaml."""
    if const.DOMAIN not in config:
        return True
    hass.data[const.DOMAIN] = config
    Hacs.hass = hass
    Hacs.configuration = Configuration(
        config[const.DOMAIN], config[const.DOMAIN].get("options")
    )
    Hacs.configuration.config_type = "yaml"
    await startup_wrapper_for_yaml(Hacs)
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
        )
    )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up this integration using UI."""
    conf = hass.data.get(const.DOMAIN)
    if config_entry.source == config_entries.SOURCE_IMPORT:
        if conf is None:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
        return False
    Hacs.hass = hass
    Hacs.configuration = Configuration(config_entry.data, config_entry.options)
    Hacs.configuration.config_type = "flow"
    Hacs.configuration.config_entry = config_entry
    config_entry.add_update_listener(reload_hacs)
    startup_result = await hacs_startup(Hacs)
    if not startup_result:
        raise ConfigEntryNotReady
    return startup_result


async def startup_wrapper_for_yaml(hacs):
    """Startup wrapper for yaml config."""
    startup_result = await hacs_startup(hacs)
    if not startup_result:
        hacs.hass.components.frontend.async_remove_panel(
            hacs.configuration.sidepanel_title.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        hacs.logger.info("Could not setup HACS, trying again in 15 min")
        async_call_later(hacs.hass, 900, startup_wrapper_for_yaml(hacs))


async def hacs_startup(hacs):
    """HACS startup tasks."""
    hacs.logger.debug(f"Configuration type: {hacs.configuration.config_type}")
    hacs.version = const.VERSION
    hacs.logger.info(const.STARTUP)
    hacs.system.config_path = hacs.hass.config.path()
    hacs.system.ha_version = HAVERSION
    hacs.system.disabled = False
    hacs.github = AIOGitHub(
        hacs.configuration.token, async_create_clientsession(hacs.hass)
    )
    hacs.data = HacsData()

    # Check minimum version
    if not check_version(hacs):
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Check custom_updater
    if not check_custom_updater(hacs):
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Set up frontend
    await setup_frontend(hacs)

    # Load HACS
    if not await load_hacs_repository(hacs):
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    val = ValidateData()
    if not val.validate_local_data_file():
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False
    else:
        if os.path.exists(f"{hacs.system.config_path}/.storage/hacs"):
            os.remove(f"{hacs.system.config_path}/.storage/hacs")

    # Restore from storefiles
    if not await hacs.data.restore():
        hacs_repo = hacs().get_by_name("custom-components/hacs")
        hacs_repo.pending_restart = True
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Add aditional categories
    if hacs.configuration.appdaemon:
        const.ELEMENT_TYPES.append("appdaemon")
    if hacs.configuration.python_script:
        const.ELEMENT_TYPES.append("python_script")
    if hacs.configuration.theme:
        const.ELEMENT_TYPES.append("theme")
    hacs.common.categories = sorted(const.ELEMENT_TYPES)

    # Setup startup tasks
    if hacs.configuration.config_type == "yaml":
        hacs.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, hacs().startup_tasks()
        )
    else:
        async_call_later(hacs.hass, 5, hacs().startup_tasks())

    # Print DEV warning
    if hacs.configuration.dev:
        hacs.logger.warning(const.DEV_MODE)
        hacs.hass.components.persistent_notification.create(
            title="HACS DEV MODE",
            message=const.DEV_MODE,
            notification_id="hacs_dev_mode",
        )

    # Add sensor
    add_sensor(hacs)

    # Set up services
    await add_services(hacs)

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
        hacs.logger.critical(
            f"You need HA version {manifest['homeassistant']} or newer to use this integration."
        )
        return False
    return True


async def load_hacs_repository(hacs):
    """Load HACS repositroy."""
    try:
        repository = hacs().get_by_name("custom-components/hacs")
        if repository is None:
            await hacs().register_repository("custom-components/hacs", "integration")
            repository = hacs().get_by_name("custom-components/hacs")
        if repository is None:
            raise AIOGitHubException("Unknown error")
        repository.status.installed = True
        repository.versions.installed = const.VERSION
        repository.status.new = False
        hacs.repo = repository.repository_object
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


def add_sensor(hacs):
    """Add sensor."""
    if hacs.configuration.config_type == "yaml":
        hacs.hass.async_create_task(
            discovery.async_load_platform(
                hacs.hass, "sensor", const.DOMAIN, {}, hacs.configuration.config
            )
        )
    else:
        hacs.hass.async_add_job(
            hacs.hass.config_entries.async_forward_entry_setup(
                hacs.configuration.config_entry, "sensor"
            )
        )


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

    async def service_hacs_load(call):
        """register a repository."""
        from homeassistant.loader import async_get_custom_components

        del hacs.hass.data["custom_components"]
        await async_get_custom_components(hacs.hass)

    hacs.hass.services.async_register("hacs", "install", service_hacs_install)
    hacs.hass.services.async_register("hacs", "register", service_hacs_register)
    hacs.hass.services.async_register("hacs", "load", service_hacs_load)


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


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    Hacs().logger.info("Disabling HACS")
    Hacs().logger.info("Removing recuring tasks")
    for task in Hacs().tasks:
        task()
    Hacs().logger.info("Removing sensor")
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    Hacs().logger.info("Removing sidepanel")
    try:
        hass.components.frontend.async_remove_panel(
            Hacs.configuration.sidepanel_title.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
    except AttributeError:
        pass
    Hacs().system.disabled = True
    Hacs().logger.info("HACS is now disabled")


async def reload_hacs(hass, config_entry):
    """Reload HACS."""
    await async_remove_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
