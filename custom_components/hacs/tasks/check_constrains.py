""""Starting setup task: Constrains"."""
from __future__ import annotations

import os

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..const import MINIMUM_HA_VERSION
from ..enums import HacsDisabledReason, HacsStage
from ..utils.version import version_left_higher_then_right
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Check env Constrains."""

    stages = [HacsStage.SETUP]

    def execute(self) -> None:
        for location in (
            self.hass.config.path("custom_components/custom_updater.py"),
            self.hass.config.path("custom_components/custom_updater/__init__.py"),
        ):
            if os.path.exists(location):
                self.log.critical(
                    "This cannot be used with custom_updater. "
                    "To use this you need to remove custom_updater form %s",
                    location,
                )
                self.hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)

        if not version_left_higher_then_right(self.hacs.core.ha_version, MINIMUM_HA_VERSION):
            self.log.critical(
                "You need HA version %s or newer to use this integration.",
                MINIMUM_HA_VERSION,
            )
            self.hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)
