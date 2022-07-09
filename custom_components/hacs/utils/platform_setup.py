"""Setup entity platforms."""
from __future__ import annotations
from typing import TYPE_CHECKING
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from ..base import HacsBase


async def async_setup_entity_platforms(
    hacs: HacsBase,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    platforms: list[str],
) -> None:
    """Set up entity platforms."""
    if hacs.core.ha_version >= "2022.8.0.dev0":
        await hass.config_entries.async_forward_entry_setups(config_entry, platforms)
    else:
        hass.config_entries.async_setup_platforms(config_entry, platforms)
