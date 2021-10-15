"""Register WS API endpoints for HACS."""
from __future__ import annotations

from homeassistant.components.websocket_api import async_register_command
from homeassistant.core import HomeAssistant

from ..api.acknowledge_critical_repository import acknowledge_critical_repository
from ..api.check_local_path import check_local_path
from ..api.get_critical_repositories import get_critical_repositories
from ..api.hacs_config import hacs_config
from ..api.hacs_removed import hacs_removed
from ..api.hacs_repositories import hacs_repositories
from ..api.hacs_repository import hacs_repository
from ..api.hacs_repository_data import hacs_repository_data
from ..api.hacs_settings import hacs_settings
from ..api.hacs_status import hacs_status
from ..base import HacsBase
from ..enums import HacsStage
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Setup the HACS websocket API."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        async_register_command(self.hass, hacs_settings)
        async_register_command(self.hass, hacs_config)
        async_register_command(self.hass, hacs_repositories)
        async_register_command(self.hass, hacs_repository)
        async_register_command(self.hass, hacs_repository_data)
        async_register_command(self.hass, check_local_path)
        async_register_command(self.hass, hacs_status)
        async_register_command(self.hass, hacs_removed)
        async_register_command(self.hass, acknowledge_critical_repository)
        async_register_command(self.hass, get_critical_repositories)
