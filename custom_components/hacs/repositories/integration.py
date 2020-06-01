"""Class for integrations in HACS."""
# pylint: disable=attribute-defined-outside-init
from integrationhelper import Logger

from homeassistant.loader import async_get_custom_components

from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.helpers.filters import get_first_directory_in_directory
from custom_components.hacs.helpers.information import get_integration_manifest
from custom_components.hacs.repositories.repository import HacsRepository


class HacsIntegration(HacsRepository):
    """Integrations in HACS."""

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.data.full_name = full_name
        self.data.category = "integration"
        self.content.path.remote = "custom_components"
        self.content.path.local = self.localpath
        self.logger = Logger(f"hacs.repository.{self.data.category}.{full_name}")

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.hacs.system.config_path}/custom_components/{self.data.domain}"

    async def async_post_installation(self):
        """Run post installation steps."""
        if self.data.config_flow:
            if self.data.full_name != "hacs/integration":
                await self.reload_custom_components()
            if self.data.first_install:
                self.pending_restart = False
                return
        self.pending_restart = True

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Custom step 1: Validate content.
        if self.data.content_in_root:
            self.content.path.remote = ""

        if self.content.path.remote == "custom_components":
            name = get_first_directory_in_directory(self.tree, "custom_components")
            if name is None:
                raise HacsException(
                    f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
                )
            self.content.path.remote = f"custom_components/{name}"

        try:
            await get_integration_manifest(self)
        except HacsException as exception:
            if self.hacs.action:
                raise HacsException(exception)
            self.logger.error(exception)

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def update_repository(self, ignore_issues=False):
        """Update."""
        await self.common_update(ignore_issues)

        if self.data.content_in_root:
            self.content.path.remote = ""

        if self.content.path.remote == "custom_components":
            name = get_first_directory_in_directory(self.tree, "custom_components")
            self.content.path.remote = f"custom_components/{name}"

        try:
            await get_integration_manifest(self)
        except HacsException as exception:
            self.logger.error(exception)

        # Set local path
        self.content.path.local = self.localpath

    async def reload_custom_components(self):
        """Reload custom_components (and config flows)in HA."""
        self.logger.info("Reloading custom_component cache")
        del self.hacs.hass.data["custom_components"]
        await async_get_custom_components(self.hacs.hass)
        self.logger.info("Custom_component cache reloaded")
