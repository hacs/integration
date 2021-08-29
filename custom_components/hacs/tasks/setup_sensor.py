""""Starting setup task: Sensor"."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from ..base import HacsBase
from ..const import DOMAIN, PLATFORMS
from ..enums import ConfigurationType, HacsStage
from .base import HacsTask


async def async_setup(hacs: HacsBase, hass: HomeAssistant) -> None:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
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
