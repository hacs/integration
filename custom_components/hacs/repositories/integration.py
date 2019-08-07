"""Class for integrations in HACS."""
import json
from homeassistant.loader import async_get_custom_components
from .repository import HacsRepository, register_repository_class


@register_repository_class
class HacsIntegration(HacsRepository):
    """Integrations in HACS."""

    category = "integration"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.manifest = None
        self.domain = None
        self.content.path.local = self.localpath

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.system.config_path}/custom_components/{self.domain}"

    @property
    def config_flow(self):
        """Return bool if integration has config_flow."""
        if self.manifest is not None:
            if self.information.full_name == "custom-components/hacs":
                return False
            return self.manifest.get("config_flow", False)
        return False

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Attach repository
        if self.repository_object is None:
            self.repository_object = await self.github.get_repo(
                self.information.full_name
            )

        # Custom step 1: Validate content.
        ccdir = await self.repository_object.get_contents("custom_components", self.ref)
        if not isinstance(ccdir, list):
            self.validate.errors.append("Repostitory structure not compliant")

        self.content.path.remote = ccdir[0].path
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

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
        await self.common_update()

        # Get integration objects.
        ccdir = await self.repository_object.get_contents("custom_components", self.ref)
        self.content.path.remote = ccdir[0].path
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

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
        manifest = None

        if "manifest.json" not in self.content.files:
            return False

        manifest = await self.repository_object.get_contents(manifest_path, self.ref)
        manifest = json.loads(manifest.content)

        if manifest:
            self.manifest = manifest
            self.information.authors = manifest["codeowners"]
            self.domain = manifest["domain"]
            self.information.name = manifest["name"]
            self.information.homeassistant_version = manifest.get("homeassistant")
            return True
        else:
            return False
