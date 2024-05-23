"""Test system health."""

import asyncio
from collections.abc import Generator
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from custom_components.hacs.base import HacsBase

from tests.common import MockedResponse, ResponseMocker, safe_json_dumps
from tests.conftest import SnapshotFixture

HACS_SYSTEM_HEALTH_DOMAIN = "Home Assistant Community Store"


async def get_system_health_info(hass: HomeAssistant, domain: str) -> dict[str, Any]:
    """Get system health info."""
    return await hass.data["system_health"][domain].info_callback(hass)


async def test_system_health(
    setup_integration: Generator,
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
) -> None:
    """Test HACS system health."""
    response_mocker.add(
        url="https://api.github.com",
        response=MockedResponse(
            content={},
            headers={"Content-Type": "application/json"},
        ),
    )
    response_mocker.add(
        url="https://raw.githubusercontent.com/hacs/integration/main/hacs.json",
        response=MockedResponse(
            content={},
            headers={"Content-Type": "application/json"},
        ),
    )
    response_mocker.add(
        url="https://data-v2.hacs.xyz/data.json",
        response=MockedResponse(
            content={},
            headers={"Content-Type": "application/json"},
        ),
    )

    assert await async_setup_component(hass, "system_health", {})
    await hass.async_block_till_done()

    info = await get_system_health_info(hass, HACS_SYSTEM_HEALTH_DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    snapshots.assert_match(safe_json_dumps(info), "system_health/system_health.json")


async def test_system_health_after_unload(
    hacs: HacsBase,
    hass: HomeAssistant,
    snapshots: SnapshotFixture,
) -> None:
    """Test HACS system health."""
    await hass.config_entries.async_unload(hacs.configuration.config_entry.entry_id)

    assert await async_setup_component(hass, "system_health", {})
    await hass.async_block_till_done()

    info = await get_system_health_info(hass, HACS_SYSTEM_HEALTH_DOMAIN)

    snapshots.assert_match(safe_json_dumps(info), "system_health/system_health_after_unload.json")


async def test_system_health_no_hacs(
    hass: HomeAssistant,
) -> None:
    """Test HACS system health."""
    assert await async_setup_component(hass, "system_health", {})
    await hass.async_block_till_done()

    with pytest.raises(KeyError, match=HACS_SYSTEM_HEALTH_DOMAIN):
        await get_system_health_info(hass, HACS_SYSTEM_HEALTH_DOMAIN)
