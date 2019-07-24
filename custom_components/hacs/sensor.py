"""Sensor platform for HACS."""
from homeassistant.helpers.entity import Entity
from .hacsbase import Hacs as hacs

from integrationhelper import Logger


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Setup sensor platform."""
    async_add_entities([HACSSensor()])


class HACSSensor(Entity):
    """HACS Sensor class."""

    def __init__(self):
        """Initialize."""
        self._state = None
        self.logger = Logger("hacs.sensor")
        self.has_update = []

    async def async_update(self):
        """Update the sensor."""
        if hacs.system.status.background_task:
            return

        updates = 0
        has_update = []
        prev_has_update = self.has_update

        for repository in hacs.repositories:
            if repository.status.pending.update:
                if repository.repository_id not in prev_has_update:
                    await repository.update()
                if repository.pending_update:
                    hacs.logger.debug(repository.repository_name)
                    updates += 1
                    has_update.append(repository.repository_id)

        self._state = updates
        self.has_update = has_update

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
        return "mdi:package"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "pending update(s)"
