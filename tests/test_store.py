"""HACS Store Test Suite."""
# pylint: disable=missing-docstring
import pytest
from homeassistant.core import HomeAssistant
from custom_components.hacs.store import async_load_from_store, async_save_to_store

REPOSITORIES = {"999999": {"name": "test1"}, "888888": {"name": "test2"}}


@pytest.mark.asyncio
async def test_save(tmpdir):
    hass = HomeAssistant()
    hass.config.config_dir = tmpdir.dirname
    await async_save_to_store(hass, "repositories", REPOSITORIES)


@pytest.mark.asyncio
async def test_load(tmpdir):
    hass = HomeAssistant()
    hass.config.config_dir = tmpdir.dirname

    repositories = await async_load_from_store(hass, "repositories")
    assert repositories["999999"]["name"] == "test1"

    repositories = await async_load_from_store(hass, "does_not_exist")
    assert not repositories
