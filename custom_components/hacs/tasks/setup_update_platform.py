""""Starting setup task: Update"."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import ConfigurationType, HacsStage
from .base import HacsTask

UPDATE_DOMAIN = "update"


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Setup the HACS update platform."""

    stages = [HacsStage.RUNNING]

    async def async_execute(self) -> None:
        """Execute the task."""
        if self.hacs.configuration.config_type == ConfigurationType.YAML:
            self.task_logger(
                self.hacs.log.info, "Update entities are only supported when using UI configuration"
            )
        elif self.hacs.core.ha_version >= "2022.4.0.dev0" and self.hacs.configuration.experimental:
            self.hass.config_entries.async_setup_platforms(
                self.hacs.configuration.config_entry, [UPDATE_DOMAIN]
            )
