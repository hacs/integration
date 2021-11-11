"""Setup HACS."""
from aiogithubapi import AIOGitHubAPIException, GitHub, GitHubAPI
from aiogithubapi.const import ACCEPT_HEADERS
from homeassistant.components.lovelace.system_health import system_health_info
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, __version__ as HAVERSION
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.loader import async_get_integration

from custom_components.hacs.const import DOMAIN, STARTUP
from custom_components.hacs.enums import ConfigurationType, HacsStage, LovelaceMode
from custom_components.hacs.hacsbase.data import HacsData
from custom_components.hacs.share import get_hacs
from custom_components.hacs.tasks.manager import HacsTaskManager


async def _async_common_setup(hass: HomeAssistant):
    """Common setup stages."""
    integration = await async_get_integration(hass, DOMAIN)

    hacs = get_hacs()

    hacs.enable_hacs()
    await hacs.async_set_stage(None)

    hacs.log.info(STARTUP.format(version=integration.version))

    hacs.integration = integration
    hacs.version = integration.version
    hacs.hass = hass
    hacs.data = HacsData()
    hacs.system.running = True
    hacs.session = async_create_clientsession(hass)
    hacs.tasks = HacsTaskManager(hacs=hacs, hass=hass)

    hacs.core.lovelace_mode = LovelaceMode.YAML
    try:
        lovelace_info = await system_health_info(hacs.hass)
        hacs.core.lovelace_mode = LovelaceMode(lovelace_info.get("mode", "yaml"))
    except Exception:  # pylint: disable=broad-except
        # If this happens, the users YAML is not valid, we assume YAML mode
        pass
    hacs.log.debug(f"Configuration type: {hacs.configuration.config_type}")
    hacs.core.config_path = hacs.hass.config.path()
    hacs.core.ha_version = HAVERSION

    await hacs.tasks.async_load()

    # Setup session for API clients
    session = async_create_clientsession(hacs.hass)

    ## Legacy GitHub client
    hacs.github = GitHub(
        hacs.configuration.token,
        session,
        headers={
            "User-Agent": f"HACS/{hacs.version}",
            "Accept": ACCEPT_HEADERS["preview"],
        },
    )

    ## New GitHub client
    hacs.githubapi = GitHubAPI(
        token=hacs.configuration.token,
        session=session,
        **{"client_name": f"HACS/{hacs.version}"},
    )

    hass.data[DOMAIN] = hacs


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hacs = get_hacs()

    if config_entry.source == SOURCE_IMPORT:
        hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
        return False
    if hass.data.get(DOMAIN) is not None:
        return False

    hacs.configuration.update_from_dict(
        {
            "config_entry": config_entry,
            "config_type": ConfigurationType.CONFIG_ENTRY,
            **config_entry.data,
            **config_entry.options,
        }
    )

    await _async_common_setup(hass)
    return await async_startup_wrapper_for_config_entry()


async def async_setup(hass, config):
    """Set up this integration using yaml."""
    hacs = get_hacs()
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

    await _async_common_setup(hass)
    await async_startup_wrapper_for_yaml()
    return True


async def async_startup_wrapper_for_config_entry():
    """Startup wrapper for ui config."""
    hacs = get_hacs()

    try:
        startup_result = await async_hacs_startup()
    except AIOGitHubAPIException:
        startup_result = False
    if not startup_result:
        raise ConfigEntryNotReady(hacs.system.disabled_reason)
    hacs.enable_hacs()
    return startup_result


async def async_startup_wrapper_for_yaml(_=None):
    """Startup wrapper for yaml config."""
    hacs = get_hacs()
    try:
        startup_result = await async_hacs_startup()
    except AIOGitHubAPIException:
        startup_result = False
    if not startup_result:
        hacs.log.info("Could not setup HACS, trying again in 15 min")
        async_call_later(hacs.hass, 900, async_startup_wrapper_for_yaml)
        return
    hacs.enable_hacs()


async def async_hacs_startup():
    """HACS startup tasks."""
    hacs = get_hacs()

    await hacs.async_set_stage(HacsStage.SETUP)
    if hacs.system.disabled:
        return False

    await hacs.async_set_stage(HacsStage.STARTUP)
    if hacs.system.disabled:
        return False

    # Setup startup tasks
    if hacs.hass.state == CoreState.running:
        async_call_later(hacs.hass, 5, hacs.startup_tasks)
    else:
        hacs.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, hacs.startup_tasks)

    # Mischief managed!
    await hacs.async_set_stage(HacsStage.WAITING)
    hacs.log.info("Setup complete, waiting for Home Assistant before startup tasks starts")

    return not hacs.system.disabled
