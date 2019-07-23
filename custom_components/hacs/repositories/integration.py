"""Class for integrations in HACS."""
from .repository import HacsRepository, register_repository_class


@register_repository_class
class HacsIntegration(HacsRepository):
    """Integrations in HACS."""

    category = "theme"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.content.path = "integration"
        self.domain = None
        self.config_flow = False

    @property
    def local_path(self):
        """Return local path."""
        return f"{self.system.config_path}/custom_components/{self.domain}"

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Custom step 1: Validate content.
        self.content.objects = await self.repository_object.get_contents(
            self.content.path, self.ref
        )
        if not isinstance(self.content.objects, list):
            self.validate.errors.append("Repostitory structure not compliant")

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.common.status.startup:
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

    async def update_repository(self):
        """Update."""
        await self.common_update()

        # Get theme objects.
        self.content.objects = await self.repository_object.get_contents(
            self.content.path, self.ref
        )

        self.information.name = self.content.objects[0].name.replace(".yaml", "")

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

        await self.get_manifest()

    async def reload_config_flows(self):
        """Reload config_flows."""

    async def get_manifest(self):
        """Get info from the manifest file."""
