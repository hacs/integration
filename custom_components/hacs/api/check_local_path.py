"""API Handler for check_local_path"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.helpers.functions.path_exsist import async_path_exsist


@websocket_api.async_response
@websocket_api.websocket_command(
    {vol.Required("type"): "hacs/check_path", vol.Optional("path"): cv.string}
)
async def check_local_path(hass, connection, msg):
    """Handle get media player cover command."""
    path = msg.get("path")
    exist = {"exist": False}

    if path is None:
        return

    if await async_path_exsist(path):
        exist["exist"] = True

    connection.send_message(websocket_api.result_message(msg["id"], exist))
