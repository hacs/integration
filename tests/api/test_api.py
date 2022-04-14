import os

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.websocket import (
    acknowledge_critical_repository,
    get_critical_repositories,
    hacs_config,
    hacs_removed,
    hacs_repositories,
    hacs_repository,
    hacs_repository_data,
    hacs_settings,
    hacs_status,
)


@pytest.mark.asyncio
async def test_check_local_path(hacs, connection, tmpdir):
    hacs.hass = HomeAssistant()
    os.makedirs(tmpdir, exist_ok=True)
    get_critical_repositories(hacs.hass, connection, {"id": 1})
    hacs_config(hacs.hass, connection, {"id": 1})
    hacs_removed(hacs.hass, connection, {"id": 1})
    hacs_repositories(hacs.hass, connection, {"id": 1})
    hacs_repository(hacs.hass, connection, {"id": 1})
    hacs_repository_data(hacs.hass, connection, {"id": 1})
    hacs_settings(hacs.hass, connection, {"id": 1})
    hacs_status(hacs.hass, connection, {"id": 1})

    acknowledge_critical_repository(hacs.hass, connection, {"repository": "test/test", "id": 1})
