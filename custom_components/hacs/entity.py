"""HACS Base entities."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, HACS_SYSTEM_ID, NAME_SHORT
from .enums import HacsDispatchEvent, HacsGitHubRepo

if TYPE_CHECKING:
    from .base import HacsBase
    from .repositories.base import HacsRepository


def system_info(hacs: HacsBase) -> dict:
    """Return system info."""
    return {
        "identifiers": {(DOMAIN, HACS_SYSTEM_ID)},
        "name": NAME_SHORT,
        "manufacturer": "hacs.xyz",
        "model": "",
        "sw_version": str(hacs.version),
        "configuration_url": "homeassistant://hacs",
        "entry_type": DeviceEntryType.SERVICE,
    }


class HacsBaseEntity(Entity):
    """Base HACS entity."""

    repository: HacsRepository | None = None
    _attr_should_poll = False

    def __init__(self, hacs: HacsBase) -> None:
        """Initialize."""
        self.hacs = hacs

    async def async_added_to_hass(self) -> None:
        """Register for status events."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                HacsDispatchEvent.REPOSITORY,
                self._update_and_write_state,
            )
        )

    @callback
    def _update(self) -> None:
        """Update the sensor."""

    async def async_update(self) -> None:
        """Manual updates of the sensor."""
        self._update()

    @callback
    def _update_and_write_state(self, _: Any) -> None:
        """Update the entity and write state."""
        self._update()
        self.async_write_ha_state()


class HacsSystemEntity(HacsBaseEntity):
    """Base system entity."""

    _attr_icon = "hacs:hacs"
    _attr_unique_id = HACS_SYSTEM_ID

    @property
    def device_info(self) -> dict[str, any]:
        """Return device information about HACS."""
        return system_info(self.hacs)


class HacsRepositoryEntity(HacsBaseEntity):
    """Base repository entity."""

    def __init__(
        self,
        hacs: HacsBase,
        repository: HacsRepository,
    ) -> None:
        """Initialize."""
        super().__init__(hacs=hacs)
        self.repository = repository
        self._attr_unique_id = str(repository.data.id)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.hacs.repositories.is_downloaded(repository_id=str(self.repository.data.id))

    @property
    def device_info(self) -> dict[str, any]:
        """Return device information about HACS."""
        if self.repository.data.full_name == HacsGitHubRepo.INTEGRATION:
            return system_info(self.hacs)

        return {
            "identifiers": {(DOMAIN, str(self.repository.data.id))},
            "name": self.repository.display_name,
            "model": self.repository.data.category,
            "manufacturer": ", ".join(
                author.replace("@", "") for author in self.repository.data.authors
            ),
            "configuration_url": "homeassistant://hacs",
            "entry_type": DeviceEntryType.SERVICE,
        }

    @callback
    def _update_and_write_state(self, data: dict) -> None:
        """Update the entity and write state."""
        if data.get("repository_id") == self.repository.data.id:
            self._update()
            self.async_write_ha_state()
