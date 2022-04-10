"""HACS Base entities."""
from __future__ import annotations

from homeassistant.core import Event, callback
from homeassistant.helpers.entity import Entity

from custom_components.hacs.enums import HacsGitHubRepo

from .base import HacsBase
from .const import DOMAIN, HACS_SYSTEM_ID, NAME_SHORT
from .repositories.base import HacsRepository


def system_info(hacs: HacsBase) -> dict:
    """Return system info."""
    info = {
        "identifiers": {(DOMAIN, HACS_SYSTEM_ID)},
        "name": NAME_SHORT,
        "manufacturer": "hacs.xyz",
        "model": "",
        "sw_version": str(hacs.version),
        "configuration_url": "homeassistant://hacs",
    }
    # LEGACY can be removed when min HA version is 2021.12
    if hacs.core.ha_version >= "2021.12.0b0":
        # pylint: disable=import-outside-toplevel
        from homeassistant.helpers.device_registry import DeviceEntryType

        info["entry_type"] = DeviceEntryType.SERVICE
    else:
        info["entry_type"] = "service"
    return info


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
            self.hass.bus.async_listen(
                event_type="hacs/repository",
                event_filter=self._filter_events,
                listener=self._update_and_write_state,
            )
        )

    @callback
    def _update(self) -> None:
        """Update the sensor."""

    async def async_update(self) -> None:
        """Manual updates of the sensor."""
        self._update()

    @callback
    def _filter_events(self, event: Event) -> bool:
        """Filter the events."""
        if self.repository is None:
            # System entities
            return True
        return event.data.get("repository_id") == self.repository.data.id

    @callback
    def _update_and_write_state(self, *_) -> None:
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

    def __init__(self, hacs: HacsBase, repository: HacsRepository) -> None:
        """Initialize."""
        super().__init__(hacs=hacs)
        self.repository = repository
        self._attr_unique_id = str(repository.data.id)

    @property
    def available(self) -> bool:
        return self.hacs.repositories.is_downloaded(repository_id=str(self.repository.data.id))

    @property
    def device_info(self) -> dict[str, any]:
        """Return device information about HACS."""
        if self.repository.data.full_name == HacsGitHubRepo.INTEGRATION:
            return system_info(self.hacs)

        info = {
            "identifiers": {(DOMAIN, str(self.repository.data.id))},
            "name": self.repository.display_name,
            "model": self.repository.data.category,
            "manufacturer": ", ".join(
                author.replace("@", "") for author in self.repository.data.authors
            ),
            "configuration_url": "homeassistant://hacs",
        }
        # LEGACY can be removed when min HA version is 2021.12
        if self.hacs.core.ha_version >= "2021.12.0b0":
            # pylint: disable=import-outside-toplevel
            from homeassistant.helpers.device_registry import DeviceEntryType

            info["entry_type"] = DeviceEntryType.SERVICE
        else:
            info["entry_type"] = "service"
        return info
