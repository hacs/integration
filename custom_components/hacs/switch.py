"""Switch entities for HACS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import HacsBase
from .const import DOMAIN
from .entity import HacsRepositoryEntity
from .repositories.base import HacsRepository


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup switch platform."""
    hacs: HacsBase = hass.data[DOMAIN]
    async_add_entities(
        HacsRepositoryPreReleaseSwitchEntity(hacs=hacs, repository=repository)
        for repository in hacs.repositories.list_downloaded
    )


class HacsRepositoryPreReleaseSwitchEntity(HacsRepositoryEntity, SwitchEntity):
    """Pre-release switch entities for repositories downloaded with HACS."""

    def __init__(self, hacs: HacsBase, repository: HacsRepository) -> None:
        """Initialize the repository pre-release switch."""
        super().__init__(hacs, repository)
        self._attr_entity_registry_enabled_default = self.repository.data.show_beta

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self.repository.display_name} pre-release"

    @property
    def is_on(self) -> bool:
        """Return if the switch ."""
        return self.repository.data.show_beta

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._handle_change(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._handle_change(False)

    async def _handle_change(self, value: bool) -> None:
        """Handle attribute value changes."""
        self.repository.data.show_beta = value
        self.repository.data.last_fetched = None  # Force update
        self.coordinator.async_update_listeners()

        await self.hacs.data.async_write()
        self.async_write_ha_state()
