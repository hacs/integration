"""WebSocket API for HACS."""
from homeassistant.components import websocket_api
from . import ws_api_handlers as handler

WS_NO_CONFIG = [
    {"type": "hacs/config", "handler": handler.hacs_config},
    {"type": "hacs/repositories", "handler": handler.hacs_repositories},
]


async def setup_ws_api(hacs):
    """Add API endpoints."""
    for api in WS_NO_CONFIG:
        schema = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({"type": api["type"]})
        hacs.hass.components.websocket_api.async_register_command(
            api["type"], api["handler"], schema
        )

        hacs.logger.info(f"Added WS endpoint {api['type']}")
