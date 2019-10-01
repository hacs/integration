"""WebSocket API for HACS."""
from homeassistant.components import websocket_api
import homeassistant.helpers.config_validation as cv
from . import ws_api_handlers as handler

WS_NO_CONFIG = [
    {"type": "hacs/config", "handler": handler.hacs_config},
    {"type": "hacs/repositories", "handler": handler.hacs_repositories},
]

WS_WITH_CONFIG = [
    {
        "type": "hacs/repository",
        "handler": handler.hacs_repository,
        "schema": {"action": cv.string, "repository": cv.string},
    }
]

WS_WITH_DATA = [
    {
        "type": "hacs/repository/data",
        "handler": handler.hacs_repository_data,
        "schema": {"action": cv.string, "repository": cv.string, "data": cv.string},
    }
]


async def setup_ws_api(hacs):
    """Add API endpoints."""
    for api in WS_NO_CONFIG:
        schema = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({"type": api["type"]})
        hacs.hass.components.websocket_api.async_register_command(
            api["type"], api["handler"], schema
        )

        hacs.logger.info(f"Added WS endpoint {api['type']}")

    for api in WS_WITH_CONFIG:
        schemadata = api["schema"]
        schemadata["type"] = api["type"]

        schema = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(schemadata)
        hacs.hass.components.websocket_api.async_register_command(
            api["type"], api["handler"], schema
        )

        hacs.logger.info(f"Added WS endpoint {api['type']}")

    for api in WS_WITH_DATA:
        schemadata = api["schema"]
        schemadata["type"] = api["type"]

        schema = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(schemadata)
        hacs.hass.components.websocket_api.async_register_command(
            api["type"], api["handler"], schema
        )

        hacs.logger.info(f"Added WS endpoint {api['type']}")
