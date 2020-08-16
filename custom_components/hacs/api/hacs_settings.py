"""API Handler for hacs_settings"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.share import get_hacs


@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/settings",
        vol.Optional("action"): cv.string,
        vol.Optional("categories"): cv.ensure_list,
    }
)
async def hacs_settings(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    logger = getLogger("api.settings")

    action = msg["action"]
    logger.debug(f"WS action '{action}'")

    if action == "set_fe_grid":
        hacs.configuration.frontend_mode = "Grid"

    elif action == "onboarding_done":
        hacs.configuration.onboarding_done = True

    elif action == "set_fe_table":
        hacs.configuration.frontend_mode = "Table"

    elif action == "set_fe_compact_true":
        hacs.configuration.frontend_compact = False

    elif action == "set_fe_compact_false":
        hacs.configuration.frontend_compact = True

    elif action == "clear_new":
        for repo in hacs.repositories:
            if repo.data.new and repo.data.category in msg.get("categories", []):
                logger.debug(f"Clearing new flag from '{repo.data.full_name}'")
                repo.data.new = False
    else:
        logger.error(f"WS action '{action}' is not valid")
    hass.bus.async_fire("hacs/config", {})
    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))
