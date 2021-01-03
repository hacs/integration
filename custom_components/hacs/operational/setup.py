"""Setup HACS."""
from aiogithubapi import AIOGitHubAPIException, GitHub
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.const import __version__ as HAVERSION
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later

from custom_components.hacs.const import DOMAIN, INTEGRATION_VERSION, STARTUP
from custom_components.hacs.enums import HacsStage
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.hacsbase.data import HacsData
from custom_components.hacs.helpers.functions.constrains import check_constrains
from custom_components.hacs.helpers.functions.remaining_github_calls import (
    get_fetch_updates_for,
)
from custom_components.hacs.operational.reload import async_reload_entry
from custom_components.hacs.operational.remove import async_remove_entry
from custom_components.hacs.operational.setup_actions.clear_storage import (
    async_clear_storage,
)
from custom_components.hacs.operational.setup_actions.frontend import (
    async_setup_frontend,
)
from custom_components.hacs.operational.setup_actions.load_hacs_repository import (
    async_load_hacs_repository,
)
from custom_components.hacs.operational.setup_actions.sensor import async_add_sensor
from custom_components.hacs.operational.setup_actions.websocket_api import (
    async_setup_hacs_websockt_api,
)
from custom_components.hacs.share import get_hacs

try:
    from homeassistant.components.lovelace import system_health_info
except ImportError:
    from homeassistant.components.lovelace.system_health import system_health_info


async def _async_common_setup(hass):
    """Common setup stages."""
    hacs = get_hacs()
    hacs.hass = hass
    hacs.system.running = True
    hacs.session = async_create_clientsession(hass)


async def async_setup_entry(hass, config_entry):
    """Set up this integration using UI."""
    from homeassistant import config_entries

    hacs = get_hacs()
    if hass.data.get(DOMAIN) is not None:
        return False
    if config_entry.source == config_entries.SOURCE_IMPORT:
        hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
        return False

    await _async_common_setup(hass)

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

    await _async_common_setup(hass)

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


async def async_startup_wrapper_for_yaml(_=None):
    """Startup wrapper for yaml config."""
    hacs = get_hacs()
    try:
        startup_result = await async_hacs_startup()
    except AIOGitHubAPIException:
        startup_result = False
    if not startup_result:
        hacs.system.disabled = True
        hacs.log.info("Could not setup HACS, trying again in 15 min")
        async_call_later(hacs.hass, 900, async_startup_wrapper_for_yaml)
        return
    hacs.system.disabled = False


async def async_hacs_startup():
    """HACS startup tasks."""
    hacs = get_hacs()
    hacs.hass.data[DOMAIN] = hacs

    try:
        lovelace_info = await system_health_info(hacs.hass)
    except TypeError:
        # If this happens, the users YAML is not valid, we assume YAML mode
        lovelace_info = {"mode": "yaml"}
    hacs.log.debug(f"Configuration type: {hacs.configuration.config_type}")
    hacs.version = INTEGRATION_VERSION
    hacs.log.info(STARTUP)
    hacs.core.config_path = hacs.hass.config.path()
    hacs.system.ha_version = HAVERSION

    # Setup websocket API
    await async_setup_hacs_websockt_api()

    # Set up frontend
    await async_setup_frontend()

    # Clear old storage files
    await async_clear_storage()

    hacs.system.lovelace_mode = lovelace_info.get("mode", "yaml")
    hacs.system.disabled = False
    hacs.github = GitHub(
        hacs.configuration.token, async_create_clientsession(hacs.hass)
    )
    hacs.data = HacsData()

    can_update = await get_fetch_updates_for(hacs.github)
    if can_update is None:
        hacs.log.critical("Your GitHub token is not valid")
        return False

    if can_update != 0:
        hacs.log.debug(f"Can update {can_update} repositories")
    else:
        hacs.log.info(
            "HACS is ratelimited, repository updates will resume when the limit is cleared, this can take up to 1 hour"
        )
        return False

    # Check HACS Constrains
    if not await hacs.hass.async_add_executor_job(check_constrains):
        if hacs.configuration.config_type == "flow":
            if hacs.configuration.config_entry is not None:
                await async_remove_entry(hacs.hass, hacs.configuration.config_entry)
        return False

    # Load HACS
    if not await async_load_hacs_repository():
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

    # Setup startup tasks
    if hacs.status.new or hacs.configuration.config_type == "flow":
        async_call_later(hacs.hass, 5, hacs.startup_tasks)
    else:
        hacs.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, hacs.startup_tasks)

    # Set up sensor
    await async_add_sensor()

    # Mischief managed!
    await hacs.async_set_stage(HacsStage.WAITING)
    hacs.log.info(
        "Setup complete, waiting for Home Assistant before startup tasks starts"
    )
    return True
