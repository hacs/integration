"""Sensor platform for HACS."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .const import DOMAIN
from .entity import HacsSystemEntity
from .enums import ConfigurationType


async def async_setup_platform(hass, _config, async_add_entities, _discovery_info=None):
    """Setup sensor platform."""
    async_add_entities([HACSSensor(hacs=hass.data.get(DOMAIN))])


async def async_setup_entry(hass, _config_entry, async_add_devices):
    """Setup sensor platform."""
    async_add_devices([HACSSensor(hacs=hass.data.get(DOMAIN))])


class HACSSensor(HacsSystemEntity, SensorEntity):
    """HACS Sensor class."""

    _attr_name = "hacs"
    _attr_native_unit_of_measurement = "pending update(s)"
    _attr_native_value = None

    @callback
    def _update(self) -> None:
        """Update the sensor."""

        repositories = [
            repository
            for repository in self.hacs.repositories.list_all
            if repository.pending_update
        ]
        self._attr_native_value = len(repositories)
        if (
            self.hacs.configuration.config_type == ConfigurationType.YAML
            or not self.hacs.configuration.experimental
        ):
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
