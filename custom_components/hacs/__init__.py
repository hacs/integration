"""
HACS gives you a powerful UI to handle downloads of all your custom needs.

For more details about this integration, please refer to the documentation at
https://hacs.xyz/
"""
from __future__ import annotations

import os
from typing import Any

from aiogithubapi import AIOGitHubAPIException, GitHub, GitHubAPI
from aiogithubapi.const import ACCEPT_HEADERS
from awesomeversion import AwesomeVersion
from homeassistant.components.lovelace.system_health import system_health_info
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform, __version__ as HAVERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.start import async_at_start
from homeassistant.loader import async_get_integration
import voluptuous as vol

from .base import HacsBase
from .const import DOMAIN, MINIMUM_HA_VERSION, STARTUP
from .data_client import HacsDataClient
from .enums import ConfigurationType, HacsDisabledReason, HacsStage, LovelaceMode
from .frontend import async_register_frontend
from .utils.configuration_schema import hacs_config_combined
from .utils.data import HacsData
from .utils.queue_manager import QueueManager
from .utils.version import version_left_higher_or_equal_then_right
from .websocket import async_register_websocket_commands

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

    hacs.set_stage(None)

    hacs.log.info(STARTUP, integration.version)

    clientsession = async_get_clientsession(hass)

    hacs.integration = integration
    hacs.version = integration.version
    hacs.configuration.dev = integration.version == "0.0.0"
    hacs.hass = hass
    hacs.queue = QueueManager(hass=hass)
    hacs.data = HacsData(hacs=hacs)
    hacs.data_client = HacsDataClient(
        session=clientsession,
        client_name=f"HACS/{integration.version}",
    )
    hacs.system.running = True
    hacs.session = clientsession

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

        for location in (
            hass.config.path("custom_components/custom_updater.py"),
            hass.config.path("custom_components/custom_updater/__init__.py"),
        ):
            if os.path.exists(location):
                hacs.log.critical(
                    "This cannot be used with custom_updater. "
                    "To use this you need to remove custom_updater form %s",
                    location,
                )

                hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)
                return False

        if not version_left_higher_or_equal_then_right(
            hacs.core.ha_version.string,
            MINIMUM_HA_VERSION,
        ):
            hacs.log.critical(
                "You need HA version %s or newer to use this integration.",
                MINIMUM_HA_VERSION,
            )
            hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)
            return False

        if not await hacs.data.restore():
            hacs.disable_hacs(HacsDisabledReason.RESTORE)
            return False

        if not hacs.configuration.experimental:
            can_update = await hacs.async_can_update()
            hacs.log.debug("Can update %s repositories", can_update)

        hacs.set_active_categories()

        async_register_websocket_commands(hass)
        async_register_frontend(hass, hacs)

        if hacs.configuration.config_type == ConfigurationType.YAML:
            hass.async_create_task(
                async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, hacs.configuration.config)
            )
            hacs.log.info("Update entities are only supported when using UI configuration")

        else:
            hass.config_entries.async_setup_platforms(
                config_entry,
                [Platform.SENSOR, Platform.UPDATE]
                if hacs.configuration.experimental
                else [Platform.SENSOR],
            )

        hacs.set_stage(HacsStage.SETUP)
        if hacs.system.disabled:
            return False

        # Schedule startup tasks
        async_at_start(hass=hass, at_start_cb=hacs.startup_tasks)

        hacs.set_stage(HacsStage.WAITING)
        hacs.log.info("Setup complete, waiting for Home Assistant before startup tasks starts")

        return not hacs.system.disabled

    async def async_try_startup(_=None):
        """Startup wrapper for yaml config."""
        try:
            startup_result = await async_startup()
        except AIOGitHubAPIException:
            startup_result = False
        if not startup_result:
            if (
                hacs.configuration.config_type == ConfigurationType.YAML
                or hacs.system.disabled_reason != HacsDisabledReason.INVALID_TOKEN
            ):
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
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))
    setup_result = await async_initialize_integration(hass=hass, config_entry=config_entry)
    hacs: HacsBase = hass.data[DOMAIN]
    return setup_result and not hacs.system.disabled


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

    platforms = ["sensor"]
    if hacs.configuration.experimental:
        platforms.append("update")

    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, platforms)

    hacs.set_stage(None)
    hacs.disable_hacs(HacsDisabledReason.REMOVED)

    hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the HACS config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
