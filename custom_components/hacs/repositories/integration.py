"""Class for integrations in HACS."""
import json
from aiogithubapi import AIOGitHubException
from integrationhelper import Logger

from homeassistant.loader import async_get_custom_components
from .repository import HacsRepository
from ..hacsbase.exceptions import HacsException


from custom_components.hacs.helpers.information import get_repository
from custom_components.hacs.helpers.filters import get_first_directory_in_directory


class HacsIntegration(HacsRepository):
    """Integrations in HACS."""

    category = "integration"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.domain = None
        self.content.path.remote = "custom_components"
        self.content.path.local = self.localpath
        self.logger = Logger(f"hacs.repository.{self.category}.{full_name}")

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.system.config_path}/custom_components/{self.domain}"

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Attach repository
        if self.repository_object is None:
            try:
                self.repository_object = await get_repository(
                    self.session, self.configuration.token, self.information.full_name
                )
            except HacsException as exception:
                self.validate.errors.append(exception)
                return self.validate.success

        # Custom step 1: Validate content.
        if self.repository_manifest:

            if self.repository_manifest.content_in_root:
                self.content.path.remote = ""

        if self.content.path.remote == "custom_components":
            name = get_first_directory_in_directory(self.tree, "custom_components")
            if not name:
                raise HacsException(
                    f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
                )
            self.content.path.remote = f"custom_components/{name}"

        if not await self.get_manifest():
            self.validate.errors.append("Missing manifest file.")

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def registration(self):
        """Registration."""
        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

        # Get the content of the manifest file.
        await self.get_manifest()

        # Set local path
        self.content.path.local = self.localpath

    async def update_repository(self):
        """Update."""
        if self.github.ratelimits.remaining == 0:
            return
        await self.common_update()

        if self.repository_manifest:
            if self.repository_manifest.content_in_root:
                self.content.path.remote = ""

        if self.content.path.remote == "custom_components":
            name = get_first_directory_in_directory(self.tree, "custom_components")
            self.content.path.remote = f"custom_components/{name}"

        await self.get_manifest()

        # Set local path
        self.content.path.local = self.localpath

    async def reload_custom_components(self):
        """Reload custom_components (and config flows)in HA."""
        self.logger.info("Reloading custom_component cache")
        del self.hass.data["custom_components"]
        await async_get_custom_components(self.hass)

    async def get_manifest(self):
        """Get info from the manifest file."""
        manifest_path = f"{self.content.path.remote}/manifest.json"
        if not manifest_path in [x.full_path for x in self.tree]:
            return False
        try:
            manifest = await self.repository_object.get_contents(
                manifest_path, self.ref
            )
            manifest = json.loads(manifest.content)
        except Exception as exception:  # pylint: disable=broad-except
            raise HacsException(f"Could not read manifest.json [{exception}]")

        if manifest:
            try:
                self.manifest = manifest
                self.information.authors = manifest["codeowners"]
                self.domain = manifest["domain"]
                self.information.name = manifest["name"]
                self.information.homeassistant_version = manifest.get("homeassistant")

                # Set local path
                self.content.path.local = self.localpath
                return True
            except KeyError as exception:
                raise HacsException(
                    f"Missing expected key {exception} in 'manifest.json'"
                )
        return False
