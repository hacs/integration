"""API Handler for hacs_config"""
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.share import get_hacs


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/config"})
async def hacs_config(_hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    config = hacs.configuration

    content = {}
    content["frontend_mode"] = config.frontend_mode
    content["frontend_compact"] = config.frontend_compact
    content["onboarding_done"] = config.onboarding_done
    content["version"] = hacs.version
    content["frontend_expected"] = hacs.frontend.version_expected
    content["frontend_running"] = hacs.frontend.version_running
    content["dev"] = config.dev
    content["debug"] = config.debug
    content["country"] = config.country
    content["experimental"] = config.experimental
    content["categories"] = hacs.common.categories

    connection.send_message(websocket_api.result_message(msg["id"], content))
