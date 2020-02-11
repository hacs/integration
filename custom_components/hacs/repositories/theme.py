"""Class for themes in HACS."""
from .repository import HacsRepository, register_repository_class
from ..hacsbase.exceptions import HacsException
from ..helpers.filters import filter_content_return_one_of_type


@register_repository_class
class HacsTheme(HacsRepository):
    """Themes in HACS."""

    category = "theme"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.content.path.remote = "themes"
        self.content.path.local = f"{self.system.config_path}/themes"
        self.content.single = False

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        compliant = False
        for treefile in self.treefiles:
            self.logger.debug(treefile)
            if treefile.startswith("themes/") and treefile.endswith(".yaml"):
                compliant = True
                break
        if not compliant:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        if self.repository_manifest:
            if self.repository_manifest.content_in_root:
                self.content.path.remote = ""

        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        if not isinstance(self.content.objects, list):
            self.validate.errors.append("Repostitory structure not compliant")

        files = filter_content_return_one_of_type(
            self.content.objects, "themes", "yaml"
        )
        self.content.files = []
        for _file in files:
            self.content.files.append(_file.name)

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

        # Set name
        self.information.name = self.content.objects[0].name.replace(".yaml", "")
        self.content.path.local = (
            f"{self.system.config_path}/themes/{self.information.name}"
        )

    async def update_repository(self):  # lgtm[py/similar-function]
        """Update."""
        if self.github.ratelimits.remaining == 0:
            return
        # Run common update steps.
        await self.common_update()

        # Get theme objects.
        if self.repository_manifest:
            if self.repository_manifest.content_in_root:
                self.content.path.remote = ""
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        files = filter_content_return_one_of_type(
            self.content.objects, "themes", "yaml"
        )
        self.content.files = []
        for _file in files:
            self.content.files.append(_file.name)

        # Update name
        self.information.file_name = self.content.objects[0].name
        self.information.name = self.content.objects[0].name.replace(".yaml", "")
        self.content.path.local = (
            f"{self.system.config_path}/themes/{self.information.name}"
        )
