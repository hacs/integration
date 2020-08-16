"""HACS Setup Test Suite."""
# pylint: disable=missing-docstring
import json
import os

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.operational.setup_actions.clear_storage import (
    async_clear_storage,
)
from custom_components.hacs.operational.setup_actions.load_hacs_repository import (
    async_load_hacs_repository,
)
from custom_components.hacs.share import get_hacs
from tests.sample_data import (
    release_data,
    repository_data,
    response_rate_limit_header,
    tree_files_base_integration,
)


@pytest.mark.asyncio
async def test_clear_storage(hacs):
    os.makedirs(f"{hacs.system.config_path}/.storage")
    with open(f"{hacs.system.config_path}/.storage/hacs", "w") as h_f:
        h_f.write("")
    assert os.path.exists(f"{hacs.system.config_path}/.storage/hacs")

    await async_clear_storage()
    assert not os.path.exists(f"{hacs.system.config_path}/.storage/hacs")

    os.makedirs(f"{hacs.system.config_path}/.storage/hacs")
    assert os.path.exists(f"{hacs.system.config_path}/.storage/hacs")

    await async_clear_storage()
    assert os.path.exists(f"{hacs.system.config_path}/.storage/hacs")
