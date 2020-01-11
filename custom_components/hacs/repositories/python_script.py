"""Class for python_scripts in HACS."""
from aiogithubapi import AIOGitHubException
from .repository import HacsRepository, register_repository_class
from ..hacsbase.exceptions import HacsException


@register_repository_class
class HacsPythonScript(HacsRepository):
    """python_scripts in HACS."""

    category = "python_script"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.content.path.remote = "python_scripts"
        self.content.path.local = f"{self.system.config_path}/python_scripts"
        self.content.single = True

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        try:
            self.content.objects = await self.repository_object.get_contents(
                self.content.path.remote, self.ref
            )
        except AIOGitHubException:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        if not isinstance(self.content.objects, list):
            self.validate.errors.append("Repostitory structure not compliant")

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

        # Set name
        self.information.name = self.content.objects[0].name.replace(".py", "")

    async def update_repository(self):  # lgtm[py/similar-function]
        """Update."""
        if self.github.ratelimits.remaining == 0:
            return
        # Run common update steps.
        await self.common_update()

        # Get python_script objects.
        if self.repository_manifest:
            if self.repository_manifest.content_in_root:
                self.content.path.remote = ""

        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

        # Update name
        self.information.name = self.content.objects[0].name.replace(".py", "")

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)
