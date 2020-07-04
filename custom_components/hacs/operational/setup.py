"""Setup HACS."""
from aiogithubapi import AIOGitHubAPIException, GitHub
from homeassistant import config_entries
from homeassistant.components.lovelace import system_health_info
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.const import __version__ as HAVERSION
from homeassistant.exceptions import ConfigEntryNotReady, ServiceNotFound
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later

from custom_components.hacs.configuration_schema import (
    FRONTEND_REPO,
    FRONTEND_REPO_URL,
)
from custom_components.hacs.const import DOMAIN, ELEMENT_TYPES, STARTUP, VERSION
from custom_components.hacs.constrains import check_constrains
from custom_components.hacs.hacs import get_hacs
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.hacsbase.data import HacsData
from custom_components.hacs.helpers.functions.remaining_github_calls import (
    get_fetch_updates_for,
)
from custom_components.hacs.operational.relaod import async_reload_entry
from custom_components.hacs.operational.remove import async_remove_entry
from custom_components.hacs.setup import (
    add_sensor,
    clear_storage,
    load_hacs_repository,
    setup_frontend,
)


def common_setup(hass):
    """Common setup stages."""
    hacs = get_hacs()
    hacs.hass = hass
    hacs.session = async_create_clientsession(hass)


async def async_setup_entry(hass, config_entry):
    """Set up this integration using UI."""
    hacs = get_hacs()
    conf = hass.data.get(DOMAIN)
    if conf is not None:
        return False
    if config_entry.source == config_entries.SOURCE_IMPORT:
        hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
        return False

    common_setup(hass)

    hacs.configuration = Configuration.from_dict(
        config_entry.data, config_entry.options
    )
    hacs.configuration.config_type = "flow"
    hacs.configuration.config_entry = config_entry

    return await async_startup_wrapper_for_config_entry()


async def async_setup(hass, config):
    """Set up this integration using yaml."""
    hacs = get_hacs()
    if DOMAIN not in config:
        return True
    if hacs.configuration and hacs.configuration.config_type == "flow":
        return True

    common_setup(hass)

    hass.data[DOMAIN] = config[DOMAIN]
    hacs.configuration = Configuration.from_dict(config[DOMAIN])
    hacs.configuration.config_type = "yaml"
    await async_startup_wrapper_for_yaml()
    return True


async def async_startup_wrapper_for_config_entry():
    """Startup wrapper for ui config."""
    hacs = get_hacs()
    hacs.configuration.config_entry.add_update_listener(async_reload_entry)
    try:
        startup_result = await async_hacs_startup()
    except AIOGitHubAPIException:
        startup_result = False
    if not startup_result:
        hacs.system.disabled = True
        raise ConfigEntryNotReady
    hacs.system.disabled = False
    return startup_result


async def async_startup_wrapper_for_yaml():
    """Startup wrapper for yaml config."""
    hacs = get_hacs()
    try:
        startup_result = await async_hacs_startup()
    except AIOGitHubAPIException:
        startup_result = False
    if not startup_result:
        hacs.system.disabled = True
        hacs.hass.components.frontend.async_remove_panel(
            hacs.configuration.sidepanel_title.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        hacs.logger.info("Could not setup HACS, trying again in 15 min")
        async_call_later(hacs.hass, 900, async_startup_wrapper_for_yaml())
        return
    hacs.system.disabled = False


async def async_hacs_startup():
    """HACS startup tasks."""
    hacs = get_hacs()

    if hacs.configuration.debug:
        try:
            await hacs.hass.services.async_call(
                "logger", "set_level", {"hacs": "debug"}
            )
            await hacs.hass.services.async_call(
                "logger", "set_level", {"queueman": "debug"}
            )
            await hacs.hass.services.async_call(
                "logger", "set_level", {"AioGitHub": "debug"}
            )
        except ServiceNotFound:
            hacs.logger.error(
                "Could not set logging level to debug, logger is not enabled"
            )

    lovelace_info = await system_health_info(hacs.hass)
    hacs.logger.debug(f"Configuration type: {hacs.configuration.config_type}")
    hacs.version = VERSION
    hacs.logger.info(STARTUP)
    hacs.system.config_path = hacs.hass.config.path()
    hacs.system.ha_version = HAVERSION

    await hacs.hass.async_add_executor_job(clear_storage)

    hacs.system.lovelace_mode = lovelace_info.get("mode", "yaml")
    hacs.system.disabled = False
    hacs.github = GitHub(
        hacs.configuration.token, async_create_clientsession(hacs.hass)
    )
    hacs.data = HacsData()

    can_update = await get_fetch_updates_for(hacs.github)
    if can_update == 0:
        hacs.logger.info("HACS is ratelimited, repository updates will resume in 1h.")
    else:
        hacs.logger.debug(f"Can update {can_update} repositories")

    # Check HACS Constrains
    if not await hacs.hass.async_add_executor_job(check_constrains):
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Set up frontend
    await setup_frontend()

    # Load HACS
    if not await load_hacs_repository():
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Restore from storefiles
    if not await hacs.data.restore():
        hacs_repo = hacs.get_by_name("hacs/integration")
        hacs_repo.pending_restart = True
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Add additional categories
    hacs.common.categories = ELEMENT_TYPES
    if hacs.configuration.appdaemon:
        hacs.common.categories.append("appdaemon")
    if hacs.configuration.netdaemon:
        hacs.common.categories.append("netdaemon")

    # Setup startup tasks
    if hacs.configuration.config_type == "yaml":
        hacs.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, hacs.startup_tasks())
    else:
        async_call_later(hacs.hass, 5, hacs.startup_tasks())

    # Show the configuration
    hacs.configuration.print()

    # Set up sensor
    await hacs.hass.async_add_executor_job(add_sensor)

    # Mischief managed!
    return True
