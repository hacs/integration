""""Starting setup task: Constrains"."""
from ..utils.version import version_left_higher_then_right
from ..const import MINIMUM_HA_VERSION
import os
from ..enums import HacsDisabledReason, HacsStage
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
    """Check env Constrains."""

    stages = [HacsStage.SETUP]

    async def execute(self) -> None:
        if not await self.hass.async_add_executor_job(self.constrain_custom_updater):
            self.hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)
        if not await self.hass.async_add_executor_job(self.constrain_version):
            self.hacs.disable_hacs(HacsDisabledReason.CONSTRAINS)

    def constrain_custom_updater(self) -> None:
        """Check if custom_updater exist."""
        for location in (
            self.hass.config.path("custom_components/custom_updater.py"),
            self.hass.config.path("custom_components/custom_updater.py"),
        ):
            if os.path.exists(location):
                self.log.critical(
                    "This cannot be used with custom_updater. "
                    "To use this you need to remove custom_updater form %s",
                    location,
                )
                return False
        return True

    def constrain_version(self) -> None:
        """Check if the version is valid."""
        if not version_left_higher_then_right(
            self.hacs.core.ha_version, MINIMUM_HA_VERSION
        ):
            self.log.critical(
                "You need HA version %s or newer to use this integration.",
                MINIMUM_HA_VERSION,
            )
            return False
        return True
