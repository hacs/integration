"""API Handler for hacs_status"""
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.share import get_hacs


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/status"})
async def hacs_status(_hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    content = {
        "startup": hacs.status.startup,
        "background_task": hacs.status.background_task,
        "lovelace_mode": hacs.system.lovelace_mode,
        "reloading_data": hacs.status.reloading_data,
        "upgrading_all": hacs.status.upgrading_all,
        "disabled": hacs.system.disabled,
        "has_pending_tasks": hacs.queue.has_pending_tasks,
        "stage": hacs.stage,
    }
    connection.send_message(websocket_api.result_message(msg["id"], content))
