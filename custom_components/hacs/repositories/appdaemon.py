"""Class for appdaemon apps in HACS."""
from aiogithubapi import AIOGitHubException
from integrationhelper import Logger

from .repository import HacsRepository
from ..hacsbase.exceptions import HacsException


class HacsAppdaemon(HacsRepository):
    """Appdaemon apps in HACS."""

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.data.full_name = full_name
        self.data.category = "appdaemon"
        self.content.path.local = self.localpath
        self.content.path.remote = "apps"
        self.logger = Logger(f"hacs.repository.{self.data.category}.{full_name}")

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.hacs.system.config_path}/appdaemon/apps/{self.data.name}"

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Custom step 1: Validate content.
        try:
            addir = await self.repository_object.get_contents("apps", self.ref)
        except AIOGitHubException:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        if not isinstance(addir, list):
            self.validate.errors.append("Repostitory structure not compliant")

        self.content.path.remote = addir[0].path
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

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

        # Set local path
        self.content.path.local = self.localpath

    async def update_repository(self):
        """Update."""
        if self.hacs.github.ratelimits.remaining == 0:
            return
        await self.common_update()

        # Get appdaemon objects.
        if self.repository_manifest:
            if self.data.content_in_root:
                self.content.path.remote = ""

        if self.content.path.remote == "apps":
            addir = await self.repository_object.get_contents(
                self.content.path.remote, self.ref
            )
            self.content.path.remote = addir[0].path
        self.content.objects = await self.repository_object.get_contents(
            self.content.path.remote, self.ref
        )

        # Set local path
        self.content.path.local = self.localpath
