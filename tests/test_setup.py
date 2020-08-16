"""HACS Setup Test Suite."""
# pylint: disable=missing-docstring
import os

import pytest

from custom_components.hacs.operational.setup_actions.clear_storage import (
    async_clear_storage,
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
