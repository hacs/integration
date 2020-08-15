"""Data Test Suite."""
import pytest
from custom_components.hacs.hacsbase.data import HacsData
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.share import get_hacs

from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_hacs_data_async_write1(hass, tmpdir):
    data = HacsData()
    hacs = get_hacs()
    repository = dummy_repository_base(hass)
    repository.data.installed = True
    repository.data.installed_version = "1"
    hacs.repositories = [repository]
    hacs.hass = hass
    hacs.hass.config.config_dir = tmpdir
    hacs.configuration = Configuration()
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_async_write2(hass, tmpdir):
    data = HacsData()
    hacs = get_hacs()
    hacs.hass = hass
    hacs.hass.config.config_dir = tmpdir
    hacs.configuration = Configuration()
    hacs.system.status.background_task = False
    hacs.system.disabled = False
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_restore(hass, tmpdir):
    data = HacsData()
    hacs = get_hacs()
    hacs.hass = hass
    hacs.hass.config.config_dir = tmpdir
    await data.restore()
