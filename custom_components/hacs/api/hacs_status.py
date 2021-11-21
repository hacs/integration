"""API Handler for hacs_status"""
from homeassistant.components import websocket_api
import voluptuous as vol

from custom_components.hacs.share import get_hacs


@websocket_api.websocket_command({vol.Required("type"): "hacs/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_status(_hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            {
                "startup": hacs.status.startup,
                "background_task": hacs.status.background_task,
                "lovelace_mode": hacs.core.lovelace_mode,
                "reloading_data": hacs.status.reloading_data,
                "upgrading_all": hacs.status.upgrading_all,
                "disabled": hacs.system.disabled,
                "disabled_reason": hacs.system.disabled_reason,
                "has_pending_tasks": hacs.queue.has_pending_tasks,
                "stage": hacs.stage,
            },
        )
    )
