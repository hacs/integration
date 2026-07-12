"""Tests for the HACS websocket API."""

from collections.abc import Generator

from homeassistant.core import HomeAssistant
import pytest

from tests.common import WSClient

UNKNOWN_REPOSITORY_ID = "1337404"


@pytest.mark.parametrize(
    ("command", "payload"),
    [
        ("hacs/repository/info", {"repository_id": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repository/ignore", {"repository": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repository/state", {"repository": UNKNOWN_REPOSITORY_ID, "state": "new"}),
        ("hacs/repository/version", {"repository": UNKNOWN_REPOSITORY_ID, "version": "1.0.0"}),
        ("hacs/repository/beta", {"repository": UNKNOWN_REPOSITORY_ID, "show_beta": True}),
        ("hacs/repository/download", {"repository": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repository/remove", {"repository": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repository/refresh", {"repository": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repository/release_notes", {"repository": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repository/releases", {"repository_id": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repositories/clear_new", {"repository": UNKNOWN_REPOSITORY_ID}),
        ("hacs/repositories/remove", {"repository": UNKNOWN_REPOSITORY_ID}),
    ],
    ids=lambda value: value.replace("hacs/", "").replace("/", "-")
    if isinstance(value, str)
    else "",
)
async def test_unknown_repository_returns_not_found(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    command: str,
    payload: dict,
):
    """Ensure all repository commands handle unknown repository ids."""
    response = await ws_client.send_and_receive_json(command, payload)

    assert response["success"] is False
    assert response["error"]["code"] == "repository_not_found"
    assert (
        response["error"]["message"]
        == f"Repository with ID ({UNKNOWN_REPOSITORY_ID}) not found"
    )
