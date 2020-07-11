from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.share import get_hacs, SHARE
from custom_components.hacs.validate import (
    async_run_repository_checks,
    async_initialize_rules,
)
from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_async_initialize_rules():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    await async_initialize_rules()


@pytest.mark.asyncio
async def test_async_run_repository_checks():
    hacs = get_hacs()
    repository = dummy_repository_integration()
    await async_run_repository_checks(repository)

    hacs.action = True
    hacs.system.running = True
    repository.tree = []
    with pytest.raises(SystemExit):
        await async_run_repository_checks(repository)

    hacs.action = False
    SHARE["rules"] = {}
    await async_run_repository_checks(repository)
    hacs.system.running = False
