"""API Handler for acknowledge_critical_repository"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store,
)


@websocket_api.async_response
@websocket_api.websocket_command(
    {vol.Required("type"): "hacs/critical", vol.Optional("repository"): cv.string}
)
async def acknowledge_critical_repository(hass, connection, msg):
    """Handle get media player cover command."""
    repository = msg["repository"]

    critical = await async_load_from_store(hass, "critical")
    for repo in critical:
        if repository == repo["repository"]:
            repo["acknowledged"] = True
    await async_save_to_store(hass, "critical", critical)
    connection.send_message(websocket_api.result_message(msg["id"], critical))
