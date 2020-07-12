"""Data Test Suite."""
from aiogithubapi.objects import repository
import pytest
import os
from homeassistant.core import HomeAssistant
from custom_components.hacs.hacsbase.data import restore_repository_data, HacsData
from custom_components.hacs.helpers.classes.repository import HacsRepository
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.share import get_hacs

from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_hacs_data_async_write1(tmpdir):
    data = HacsData()
    hacs = get_hacs()
    repository = dummy_repository_base()
    repository.data.installed = True
    repository.data.installed_version = "1"
    hacs.repositories = [repository]
    hacs.hass = HomeAssistant()
    hacs.hass.config.config_dir = tmpdir
    hacs.configuration = Configuration()
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_async_write2(tmpdir):
    data = HacsData()
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.hass.config.config_dir = tmpdir
    hacs.configuration = Configuration()
    hacs.system.status.background_task = False
    hacs.system.disabled = False
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_restore(tmpdir):
    data = HacsData()
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.hass.config.config_dir = tmpdir
    await data.restore()


def test_restore_repository_data():
    repo = HacsRepository()
    data = {"description": "test", "installed": True, "full_name": "hacs/integration"}
    restore_repository_data(repo, data)
    assert repo.data.description == "test"
