""""Starting setup task: Constrains"."""
from __future__ import annotations

import os

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..const import MINIMUM_HA_VERSION
from ..enums import HacsDisabledReason, HacsStage
from ..utils.version import version_left_higher_or_equal_then_right
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Check env Constrains."""

    stages = [HacsStage.SETUP]

    def execute(self) -> None:
        """Execute the task."""
        for location in (
            self.hass.config.path("custom_components/custom_updater.py"),
            self.hass.config.path("custom_components/custom_updater/__init__.py"),
        ):
            if os.path.exists(location):
                self.task_logger(
                    self.hacs.log.critical,
                    "This cannot be used with custom_updater. "
                    f"To use this you need to remove custom_updater form {location}",
                )

                self.hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)

        if not version_left_higher_or_equal_then_right(
            self.hacs.core.ha_version.string,
            MINIMUM_HA_VERSION,
        ):
            self.task_logger(
                self.hacs.log.critical,
                f"You need HA version {MINIMUM_HA_VERSION} or newer to use this integration.",
            )
            self.hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)
