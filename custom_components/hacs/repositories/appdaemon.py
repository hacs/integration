"""Class for appdaemon apps in HACS."""
from .repository import HacsRepository, register_repository_class


@register_repository_class
class HacsAppdaemon(HacsRepository):
    """Appdaemon apps in HACS."""

    category = "appdaemon"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.content.path.local = self.localpath
        self.content.path.remote = "apps"

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.system.config_path}/appdaemon/apps/{self.information.name}"

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Custom step 1: Validate content.
        addir = await self.repository_object.get_contents("apps", self.ref)
        if not isinstance(addir, list):
            self.validate.errors.append("Repostitory structure not compliant")

        self.content.path.remote = addir[0].path
        self.information.name = addir[0].name
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

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

        # Set local path
        self.content.path.local = self.localpath

    async def update_repository(self):
        """Update."""
        await self.common_update()

        # Get appdaemon objects.
        if self.repository_manifest:
            if self.repository_manifest.content_in_root:
                self.content.path.remote = ""

        if self.content.path.remote == "apps":
            addir = await self.repository_object.get_contents(
                self.content.path.remote, self.ref
            )
            self.content.path.remote = addir[0].path
            self.information.name = addir[0].name
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

        # Set local path
        self.content.path.local = self.localpath
