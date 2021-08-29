# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import MagicMock

import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_setup_frontend(hacs: HacsBase):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("setup_frontend")

    assert task

    hacs.hass.http = MagicMock()
    hacs.hass.components.frontend = MagicMock()
    await task.execute_task()

    assert hacs.hass.http.register_view.call_count == 0

    assert hacs.hass.http.register_static_path.call_count == 4
    assert hacs.hass.http.register_static_path.mock_calls[0].args[0] == "/hacsfiles/themes"
    assert hacs.hass.http.register_static_path.mock_calls[1].args[0] == "/hacsfiles/frontend"
    assert hacs.hass.http.register_static_path.mock_calls[2].args[0] == "/hacsfiles/iconset.js"
    assert hacs.hass.http.register_static_path.mock_calls[3].args[0] == "/hacsfiles"

    assert hacs.hass.components.frontend.async_register_built_in_panel.call_count == 1

    hacs.configuration.frontend_repo_url = "lorem_ipsum"


@pytest.mark.asyncio
async def test_setup_frontend_dev(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("setup_frontend")

    assert task

    hacs.configuration.frontend_repo_url = "lorem_ipsum"

    hacs.hass.http = MagicMock()
    hacs.hass.components.frontend = MagicMock()
    await task.execute_task()

    assert hacs.hass.http.register_view.call_count == 1

    assert "Frontend development mode enabled. Do not run in production!" in caplog.text
