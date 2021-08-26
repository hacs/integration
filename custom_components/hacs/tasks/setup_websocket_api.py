"""Register WS API endpoints for HACS."""
from homeassistant.components.websocket_api import async_register_command

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
from ..enums import HacsStage
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
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
