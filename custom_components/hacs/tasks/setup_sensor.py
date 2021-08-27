""""Starting setup task: Sensor"."""

from homeassistant.helpers.discovery import async_load_platform

from ..const import DOMAIN, PLATFORMS
from ..enums import ConfigurationType, HacsStage
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
    """Setup the HACS sensor platform."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        if self.hacs.configuration.config_type == ConfigurationType.YAML:
            self.hass.async_create_task(
                async_load_platform(self.hass, "sensor", DOMAIN, {}, self.hacs.configuration.config)
            )
        else:
            self.hass.config_entries.async_setup_platforms(
                self.hacs.configuration.config_entry, PLATFORMS
            )
