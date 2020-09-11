"""Register WS API endpoints for HACS."""
from homeassistant.components import websocket_api

from custom_components.hacs.api.acknowledge_critical_repository import (
    acknowledge_critical_repository,
)
from custom_components.hacs.api.check_local_path import check_local_path
from custom_components.hacs.api.get_critical_repositories import (
    get_critical_repositories,
)
from custom_components.hacs.api.hacs_config import hacs_config
from custom_components.hacs.api.hacs_removed import hacs_removed
from custom_components.hacs.api.hacs_repositories import hacs_repositories
from custom_components.hacs.api.hacs_repository import hacs_repository
from custom_components.hacs.api.hacs_repository_data import hacs_repository_data
from custom_components.hacs.api.hacs_settings import hacs_settings
from custom_components.hacs.api.hacs_status import hacs_status
from custom_components.hacs.share import get_hacs
from ...enums import HacsSetupTask


async def async_setup_hacs_websockt_api():
    """Set up WS API handlers."""
    hacs = get_hacs()
    hacs.log.info("Setup task %s", HacsSetupTask.WEBSOCKET)
    websocket_api.async_register_command(hacs.hass, hacs_settings)
    websocket_api.async_register_command(hacs.hass, hacs_config)
    websocket_api.async_register_command(hacs.hass, hacs_repositories)
    websocket_api.async_register_command(hacs.hass, hacs_repository)
    websocket_api.async_register_command(hacs.hass, hacs_repository_data)
    websocket_api.async_register_command(hacs.hass, check_local_path)
    websocket_api.async_register_command(hacs.hass, hacs_status)
    websocket_api.async_register_command(hacs.hass, hacs_removed)
    websocket_api.async_register_command(hacs.hass, acknowledge_critical_repository)
    websocket_api.async_register_command(hacs.hass, get_critical_repositories)
