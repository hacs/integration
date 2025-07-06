"""Tests for websocket repositories commands when HACS is not initialized."""

from collections.abc import Generator

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.const import DOMAIN

from tests.common import WSClient, get_hacs


@pytest.mark.parametrize(
    "command,payload",
    [
        ("hacs/repositories/list", {}),
        ("hacs/repositories/list", {"categories": ["integration"]}),
        ("hacs/repositories/clear_new", {}),
        ("hacs/repositories/clear_new", {"categories": ["plugin"]}),
        ("hacs/repositories/clear_new", {"repository": "test/repo"}),
        ("hacs/repositories/removed", {}),
        ("hacs/repositories/add", {"repository": "test/repo", "category": "integration"}),
        ("hacs/repositories/remove", {"repository": "123"}),
    ],
)
async def test_websocket_repositories_commands_hacs_not_initialized(
    hass: HomeAssistant,
    ws_client: WSClient,
    command: str,
    payload: dict,
):
    """Test that websocket repository commands return proper errors when HACS is not initialized."""
    # Ensure HACS is not in hass.data (not initialized)
    hass.data.pop(DOMAIN, None)
    
    # Send websocket command
    response = await ws_client.send_and_receive_json(command, payload)
    
    # Verify error response
    assert response["success"] is False
    assert response["error"]["code"] == "hacs_not_initialized"
    assert response["error"]["message"] == "HACS is not properly initialized"


async def test_websocket_repositories_list_with_hacs_initialized(
    hass: HomeAssistant,
    setup_integration: Generator,  # This sets up HACS properly
    ws_client: WSClient,
):
    """Test that websocket works normally when HACS is properly initialized."""
    # Verify HACS is properly initialized
    hacs = get_hacs(hass)
    assert hacs is not None
    
    # Send websocket command - should work normally
    response = await ws_client.send_and_receive_json("hacs/repositories/list", {})
    
    # Verify successful response (should be a list, not an error)
    assert response["success"] is True
    assert "result" in response
    assert isinstance(response["result"], list)