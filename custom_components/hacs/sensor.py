"""Sensor platform for HACS."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .base import HacsBase
from .const import DOMAIN, NAME_SHORT


async def async_setup_platform(hass, _config, async_add_entities, _discovery_info=None):
    """Setup sensor platform."""
    async_add_entities([HACSSensor(hacs=hass.data.get(DOMAIN))])


async def async_setup_entry(hass, _config_entry, async_add_devices):
    """Setup sensor platform."""
    async_add_devices([HACSSensor(hacs=hass.data.get(DOMAIN))])


class HACSSensor(SensorEntity):
    """HACS Sensor class."""

    _attr_should_poll = False
    _attr_unique_id = "0717a0cd-745c-48fd-9b16-c8534c9704f9-bc944b0f-fd42-4a58-a072-ade38d1444cd"
    _attr_name = "hacs"
    _attr_icon = "hacs:hacs"
    _attr_unit_of_measurement = "pending update(s)"

    def __init__(self, hacs: HacsBase) -> None:
        """Initialize."""
        self.hacs = hacs
        self._attr_native_value = None

    async def async_update(self) -> None:
        """Manual updates of the sensor."""
        self._update()

    @callback
    def _update_and_write_state(self, *_) -> None:
        """Update the sensor and write state."""
        self._update()
        self.async_write_ha_state()

    @property
    def device_info(self) -> dict[str, any]:
        """Return device information about HACS."""
        info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": NAME_SHORT,
            "manufacturer": "hacs.xyz",
            "model": "",
            "sw_version": str(self.hacs.version),
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

    @callback
    def _update(self) -> None:
        """Update the sensor."""
        if self.hacs.status.background_task:
            return

        repositories = [
            repository
            for repository in self.hacs.repositories.list_all
            if repository.pending_update
        ]
        self._attr_native_value = len(repositories)
        self._attr_extra_state_attributes = {
            "repositories": [
                {
                    "name": repository.data.full_name,
                    "display_name": repository.display_name,
                    "installed_version": repository.display_installed_version,
                    "available_version": repository.display_available_version,
                }
                for repository in repositories
            ]
        }

    async def async_added_to_hass(self) -> None:
        """Register for status events."""
        self.async_on_remove(
            self.hass.bus.async_listen("hacs/status", self._update_and_write_state)
        )
