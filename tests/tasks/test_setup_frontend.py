# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp.client import request
from aresponses import ResponsesMockServer
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.tasks.setup_frontend import HacsFrontendDev


@pytest.mark.asyncio
async def test_setup_frontend(hacs: HacsBase):
    task = hacs.tasks.get("setup_frontend")

    assert task

    with patch(
        "homeassistant.components.http.HomeAssistantHTTP.register_view", return_value=MagicMock()
    ) as mock_register_view, patch(
        "homeassistant.components.http.HomeAssistantHTTP.register_static_path",
        return_value=MagicMock(),
    ) as mock_register_static_path, patch(
        "homeassistant.components.frontend.async_register_built_in_panel", return_value=AsyncMock()
    ) as mock_async_register_built_in_panel:

        await task.execute_task()

        assert mock_register_view.call_count == 0

        assert mock_register_static_path.call_count == 4
        assert mock_register_static_path.mock_calls[0].args[0] == "/hacsfiles/themes"
        assert mock_register_static_path.mock_calls[1].args[0] == "/hacsfiles/frontend"
        assert mock_register_static_path.mock_calls[2].args[0] == "/hacsfiles/iconset.js"
        assert mock_register_static_path.mock_calls[3].args[0] == "/hacsfiles"

        assert mock_async_register_built_in_panel.call_count == 1


@pytest.mark.asyncio
async def test_setup_frontend_dev(
    hacs: HacsBase, caplog: pytest.LogCaptureFixture, aresponses: ResponsesMockServer
):
    task = hacs.tasks.get("setup_frontend")

    assert task

    hacs.configuration.frontend_repo_url = "http://lorem.ipsum"

    await task.execute_task()

    assert "Frontend development mode enabled. Do not run in production!" in caplog.text

    view = HacsFrontendDev()

    aresponses.add(
        "lorem.ipsum",
        "/index.html",
        "get",
        aresponses.Response(body="dev_server_response"),
    )

    resp = await view.get(MagicMock(app={"hass": hacs.hass}), "index.html")

    assert resp.headers["Content-Type"] == "application/javascript"
    assert resp.body == b"dev_server_response"
