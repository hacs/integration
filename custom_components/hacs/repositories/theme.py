"""Class for themes in HACS."""
from integrationhelper import Logger
from .repository import HacsRepository
from ..hacsbase.exceptions import HacsException
from ..helpers.information import find_file_name


class HacsTheme(HacsRepository):
    """Themes in HACS."""

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.data.full_name = full_name
        self.data.category = "theme"
        self.content.path.remote = "themes"
        self.content.path.local = f"{self.hacs.system.config_path}/themes/"
        self.content.single = False
        self.logger = Logger(f"hacs.repository.{self.data.category}.{full_name}")

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        compliant = False
        for treefile in self.treefiles:
            if treefile.startswith("themes/") and treefile.endswith(".yaml"):
                compliant = True
                break
        if not compliant:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        if self.data.content_in_root:
            self.content.path.remote = ""

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def registration(self, ref=None):
        """Registration."""
        if ref is not None:
            self.ref = ref
            self.force_branch = True
        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

        # Set name
        find_file_name(self)
        self.content.path.local = f"{self.hacs.system.config_path}/themes/{self.data.file_name.replace('.yaml', '')}"

    async def update_repository(self):  # lgtm[py/similar-function]
        """Update."""
        if self.hacs.github.ratelimits.remaining == 0:
            return
        # Run common update steps.
        await self.common_update()

        # Get theme objects.
        if self.data.content_in_root:
            self.content.path.remote = ""

        # Update name
        find_file_name(self)
        self.content.path.local = f"{self.hacs.system.config_path}/themes/{self.data.file_name.replace('.yaml', '')}"
