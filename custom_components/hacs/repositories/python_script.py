"""Class for python_scripts in HACS."""
from integrationhelper import Logger

from .repository import HacsRepository
from ..hacsbase.exceptions import HacsException
from ..helpers.information import find_file_name


class HacsPythonScript(HacsRepository):
    """python_scripts in HACS."""

    category = "python_script"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.data.full_name = full_name
        self.data.category = "python_script"
        self.content.path.remote = "python_scripts"
        self.content.path.local = f"{self.hacs.system.config_path}/python_scripts"
        self.content.single = True
        self.logger = Logger(f"hacs.repository.{self.data.category}.{full_name}")

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        if self.data.content_in_root:
            self.content.path.remote = ""

        compliant = False
        for treefile in self.treefiles:
            if treefile.startswith(f"{self.content.path.remote}") and treefile.endswith(
                ".py"
            ):
                compliant = True
                break
        if not compliant:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def registration(self):
        """Registration."""
        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

        # Set name
        find_file_name(self)

    async def update_repository(self):  # lgtm[py/similar-function]
        """Update."""
        if self.hacs.github.ratelimits.remaining == 0:
            return
        # Run common update steps.
        await self.common_update()

        # Get python_script objects.
        if self.data.content_in_root:
            self.content.path.remote = ""

        compliant = False
        for treefile in self.treefiles:
            if treefile.startswith(f"{self.content.path.remote}") and treefile.endswith(
                ".py"
            ):
                compliant = True
                break
        if not compliant:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        # Update name
        find_file_name(self)
