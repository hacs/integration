"""Data Test Suite."""
import pytest

from custom_components.hacs.hacsbase.data import HacsData


@pytest.mark.asyncio
async def test_hacs_data_async_write1(hacs, repository):
    data = HacsData()
    repository.data.installed = True
    repository.data.installed_version = "1"
    hacs.repositories = [repository]
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_async_write2(hacs):
    data = HacsData()
    hacs.status.background_task = False
    hacs.system.disabled = False
    hacs.repositories = []
    await data.async_write()


@pytest.mark.asyncio
async def test_hacs_data_restore(hacs):
    data = HacsData()
    await data.restore()
