"""
HACS gives you a powerful UI to handle downloads of all your custom needs.

For more details about this integration, please refer to the documentation at
https://hacs.xyz/
"""
from __future__ import annotations

from typing import Any

from aiogithubapi import AIOGitHubAPIException, GitHub, GitHubAPI
from aiogithubapi.const import ACCEPT_HEADERS
from awesomeversion import AwesomeVersion
from homeassistant.components.lovelace.system_health import system_health_info
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as HAVERSION
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.loader import async_get_integration
import voluptuous as vol

from .base import HacsBase
from .const import DOMAIN, PLATFORMS, STARTUP
from .enums import ConfigurationType, HacsDisabledReason, HacsStage, LovelaceMode
from .tasks.manager import HacsTaskManager
from .utils.configuration_schema import hacs_config_combined
from .utils.data import HacsData
from .utils.queue_manager import QueueManager
from .validate.manager import ValidationManager

CONFIG_SCHEMA = vol.Schema({DOMAIN: hacs_config_combined()}, extra=vol.ALLOW_EXTRA)


async def async_initialize_integration(
    hass: HomeAssistant,
    *,
    config_entry: ConfigEntry | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """Initialize the integration"""
    hass.data[DOMAIN] = hacs = HacsBase()
    hacs.enable_hacs()

    if config is not None:
        if DOMAIN not in config:
            return True
        if hacs.configuration.config_type == ConfigurationType.CONFIG_ENTRY:
            return True
        hacs.configuration.update_from_dict(
            {
                "config_type": ConfigurationType.YAML,
                **config[DOMAIN],
                "config": config[DOMAIN],
            }
        )

    if config_entry is not None:
        if config_entry.source == SOURCE_IMPORT:
            hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
            return False

        hacs.configuration.update_from_dict(
            {
                "config_entry": config_entry,
                "config_type": ConfigurationType.CONFIG_ENTRY,
                **config_entry.data,
                **config_entry.options,
            }
        )

    integration = await async_get_integration(hass, DOMAIN)

    await hacs.async_set_stage(None)

    hacs.log.info(STARTUP, integration.version)

    clientsession = async_get_clientsession(hass)

    hacs.integration = integration
    hacs.version = integration.version
    hacs.hass = hass
    hacs.queue = QueueManager(hass=hass)
    hacs.data = HacsData(hacs=hacs)
    hacs.system.running = True
    hacs.session = clientsession
    hacs.tasks = HacsTaskManager(hacs=hacs, hass=hass)
    hacs.validation = ValidationManager(hacs=hacs, hass=hass)

    hacs.core.lovelace_mode = LovelaceMode.YAML
    try:
        lovelace_info = await system_health_info(hacs.hass)
        hacs.core.lovelace_mode = LovelaceMode(lovelace_info.get("mode", "yaml"))
    except BaseException:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
        # If this happens, the users YAML is not valid, we assume YAML mode
        pass
    hacs.log.debug("Configuration type: %s", hacs.configuration.config_type)
    hacs.core.config_path = hacs.hass.config.path()

    if hacs.core.ha_version is None:
        hacs.core.ha_version = AwesomeVersion(HAVERSION)

    await hacs.tasks.async_load()

    ## Legacy GitHub client
    hacs.github = GitHub(
        hacs.configuration.token,
        clientsession,
        headers={
            "User-Agent": f"HACS/{hacs.version}",
            "Accept": ACCEPT_HEADERS["preview"],
        },
    )

    ## New GitHub client
    hacs.githubapi = GitHubAPI(
        token=hacs.configuration.token,
        session=clientsession,
        **{"client_name": f"HACS/{hacs.version}"},
    )

    async def async_startup():
        """HACS startup tasks."""
        hacs.enable_hacs()

        await hacs.async_set_stage(HacsStage.SETUP)
        if hacs.system.disabled:
            return False

        # Setup startup tasks
        if hacs.hass.state == CoreState.running:
            async_call_later(hacs.hass, 5, hacs.startup_tasks)
        else:
            hacs.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, hacs.startup_tasks)

        await hacs.async_set_stage(HacsStage.WAITING)
        hacs.log.info("Setup complete, waiting for Home Assistant before startup tasks starts")

        return not hacs.system.disabled

    async def async_try_startup(_=None):
        """Startup wrapper for yaml config."""
        try:
            startup_result = await async_startup()
        except AIOGitHubAPIException:
            startup_result = False
        if not startup_result:
            hacs.log.info("Could not setup HACS, trying again in 15 min")
            async_call_later(hass, 900, async_try_startup)
            return
        hacs.enable_hacs()

    await async_try_startup()

    # Mischief managed!
    return True


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up this integration using yaml."""
    return await async_initialize_integration(hass=hass, config=config)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.add_update_listener(async_reload_entry)
    return await async_initialize_integration(hass=hass, config_entry=config_entry)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    hacs: HacsBase = hass.data[DOMAIN]

    # Clear out pending queue
    hacs.queue.clear()

    for task in hacs.recuring_tasks:
        # Cancel all pending tasks
        task()

    # Store data
    await hacs.data.async_write(force=True)

    try:
        if hass.data.get("frontend_panels", {}).get("hacs"):
            hacs.log.info("Removing sidepanel")
            hass.components.frontend.async_remove_panel("hacs")
    except AttributeError:
        pass

    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    hacs.disable_hacs(HacsDisabledReason.REMOVED)
    hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the HACS config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
