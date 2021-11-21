"""API Handler for hacs_config"""
from homeassistant.components import websocket_api
import voluptuous as vol

from custom_components.hacs.share import get_hacs


@websocket_api.websocket_command({vol.Required("type"): "hacs/config"})
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_config(_hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            {
                "frontend_mode": hacs.configuration.frontend_mode,
                "frontend_compact": hacs.configuration.frontend_compact,
                "onboarding_done": hacs.configuration.onboarding_done,
                "version": hacs.version,
                "frontend_expected": hacs.frontend.version_expected,
                "frontend_running": hacs.frontend.version_running,
                "dev": hacs.configuration.dev,
                "debug": hacs.configuration.debug,
                "country": hacs.configuration.country,
                "experimental": hacs.configuration.experimental,
                "categories": hacs.common.categories,
            },
        )
    )
