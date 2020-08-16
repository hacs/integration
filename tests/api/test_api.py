import os

import pytest
from homeassistant.core import HomeAssistant

from custom_components.hacs.api.acknowledge_critical_repository import (
    acknowledge_critical_repository,
)
from custom_components.hacs.api.check_local_path import check_local_path
from custom_components.hacs.api.get_critical_repositories import (
    get_critical_repositories,
)
from custom_components.hacs.api.hacs_config import hacs_config
from custom_components.hacs.api.hacs_removed import hacs_removed
from custom_components.hacs.api.hacs_repositories import hacs_repositories
from custom_components.hacs.api.hacs_repository import hacs_repository
from custom_components.hacs.api.hacs_repository_data import hacs_repository_data
from custom_components.hacs.api.hacs_settings import hacs_settings
from custom_components.hacs.api.hacs_status import hacs_status


@pytest.mark.asyncio
async def test_check_local_path(hacs, connection, tmpdir):
    hacs.hass = HomeAssistant()
    os.makedirs(tmpdir, exist_ok=True)
    check_local_path(hacs.hass, connection, {"path": tmpdir, "id": 1})
    check_local_path(hacs.hass, connection, {"id": 1})
    get_critical_repositories(hacs.hass, connection, {"id": 1})
    hacs_config(hacs.hass, connection, {"id": 1})
    hacs_removed(hacs.hass, connection, {"id": 1})
    hacs_repositories(hacs.hass, connection, {"id": 1})
    hacs_repository(hacs.hass, connection, {"id": 1})
    hacs_repository_data(hacs.hass, connection, {"id": 1})
    hacs_settings(hacs.hass, connection, {"id": 1})
    hacs_status(hacs.hass, connection, {"id": 1})

    acknowledge_critical_repository(
        hacs.hass, connection, {"repository": "test/test", "id": 1}
    )
