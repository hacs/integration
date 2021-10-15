"""Starting setup task: extra stores."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsCategory, HacsStage
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Set up extra stores in HACS if enabled in Home Assistant."""

    stages = [HacsStage.SETUP]

    def execute(self) -> None:
        self.hacs.common.categories = set()
        for category in (HacsCategory.INTEGRATION, HacsCategory.PLUGIN):
            self.hacs.enable_hacs_category(HacsCategory(category))

        if HacsCategory.PYTHON_SCRIPT in self.hacs.hass.config.components:
            self.hacs.enable_hacs_category(HacsCategory.PYTHON_SCRIPT)

        if self.hacs.hass.services.has_service("frontend", "reload_themes"):
            self.hacs.enable_hacs_category(HacsCategory.THEME)

        if self.hacs.configuration.appdaemon:
            self.hacs.enable_hacs_category(HacsCategory.APPDAEMON)
        if self.hacs.configuration.netdaemon:
            self.hacs.enable_hacs_category(HacsCategory.NETDAEMON)
