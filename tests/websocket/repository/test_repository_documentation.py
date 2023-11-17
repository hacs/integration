"""Test the repository documentation websocket command."""
from unittest.mock import patch
import pytest
from homeassistant.components import websocket_api

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsRepository

from custom_components.hacs.websocket.repository import hacs_repository_documentation
from tests.common import WSClient
import json
from yarl import URL


async_download_file_response = {
    "3/hacs.json": json.dumps({"documentation": {"en": "docs/en.md", "nb": "docs/nb.md"}}),
    "3/docs/en.md": "english content".encode(),
    "3/docs/nb.md": "norwegian content".encode(),
    "4/hacs.json": json.dumps({"documentation": {}}),
}

@pytest.mark.parametrize("language,content,version", [
    ("en", "english content", "3"),
    ("nb", "norwegian content", "3"),
    ("invalid", "english content", "3"),
    (None, None, "4"),
    (None, None, "5"),
])
@pytest.mark.asyncio
async def test_websocket_repository_documentation(hacs: HacsBase,repository: HacsRepository, ws_client: WSClient, language: str, content: str, version: str):
    """Test the repository_documentation websocket command."""
    websocket_api.async_register_command(hacs.hass, hacs_repository_documentation)
    hacs.repositories.register(repository)

    repository.data.last_version = version

    payload = {"repository_id": repository.data.id}
    if language:
        payload["language"] = language


    async def async_download_file(url: str, **kwargs):
        return async_download_file_response.get(URL(url).path.removeprefix(f"/{repository.data.full_name}/"))


    with patch("custom_components.hacs.base.HacsBase.async_download_file", side_effect=async_download_file):
        result = await ws_client.send_and_receive_json(
            type="hacs/repository/documentation",
            payload=payload,
        )
    assert result["result"] == {'content': content}
