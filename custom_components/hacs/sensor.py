"""Sensor platform for HACS."""
# pylint: disable=unused-argument
from homeassistant.helpers.entity import Entity

from custom_components.hacs.const import DOMAIN, NAME_SHORT, VERSION
from custom_components.hacs.share import get_hacs


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup sensor platform."""
    async_add_entities([HACSSensor()])


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Setup sensor platform."""
    async_add_devices([HACSSensor()])


class HACSDevice(Entity):
    """HACS Device class."""

    @property
    def device_info(self):
        """Return device information about HACS."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": NAME_SHORT,
            "manufacturer": "hacs.xyz",
            "model": "",
            "sw_version": VERSION,
            "type": "service",
        }


class HACSSensor(HACSDevice):
    """HACS Sensor class."""

    def __init__(self):
        """Initialize."""
        self._state = None
        self.repositories = []

    async def async_update(self):
        """Update the sensor."""
        hacs = get_hacs()
        if hacs.system.status.background_task:
            return

        self.repositories = []

        for repository in hacs.repositories:
            if (
                repository.pending_upgrade
                and repository.data.category in hacs.common.categories
            ):
                self.repositories.append(repository)
        self._state = len(self.repositories)

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return (
            "0717a0cd-745c-48fd-9b16-c8534c9704f9-bc944b0f-fd42-4a58-a072-ade38d1444cd"
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return "hacs"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "hacs:hacs"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "pending update(s)"

    @property
    def device_state_attributes(self):
        """Return attributes for the sensor."""
        repositories = []
        for repository in self.repositories:
            repositories.append(
                {
                    "name": repository.data.full_name,
                    "display_name": repository.display_name,
                    "installed_version": repository.display_installed_version,
                    "available_version": repository.display_available_version,
                }
            )
        return {"repositories": repositories}
