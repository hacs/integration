"""API Handler for hacs_settings"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.hacs import get_hacs


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
    action = msg["action"]
    hacs.logger.debug(f"WS action '{action}'")

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

    elif action == "upgrade_all":
        hacs.system.status.upgrading_all = True
        hacs.system.status.background_task = True
        hass.bus.async_fire("hacs/status", {})
        for repository in hacs.repositories:
            if repository.pending_upgrade:
                repository.data.selected_tag = None
                await repository.async_install()
        hacs.system.status.upgrading_all = False
        hacs.system.status.background_task = False
        hass.bus.async_fire("hacs/status", {})
        hass.bus.async_fire("hacs/repository", {})

    elif action == "clear_new":
        for repo in hacs.repositories:
            if repo.data.new and repo.data.category in msg.get("categories", []):
                hacs.logger.debug(f"Clearing new flag from '{repo.data.full_name}'")
                repo.data.new = False
    else:
        hacs.logger.error(f"WS action '{action}' is not valid")
    hass.bus.async_fire("hacs/config", {})
    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))
