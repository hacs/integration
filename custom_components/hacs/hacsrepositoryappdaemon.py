"""Blueprint for HacsRepositoryAppDaemon."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
import logging
import json

from .blueprints import HacsRepositoryBase
from .exceptions import HacsRequirement

_LOGGER = logging.getLogger("custom_components.hacs.repository")


class HacsRepositoryAppDaemon(HacsRepositoryBase):
    """
    Set up a HacsRepositoryAppDaemon object.

    repository_name(str): The full name of a repository
    (example: awesome-dev/awesome-repo)
    """

    def __init__(self, repository_name: str, repositoryobject=None):
        """Initialize a HacsRepositoryAppDaemon object."""
        super().__init__()
        self.repository = repositoryobject
        self.repository_name = repository_name
        self.repository_type = "appdaemon"
        self.manifest_content = None
        self.name = repository_name.split("/")[-1]

    async def update(self):
        """Run update tasks."""
        if await self.common_update():
            return
        await self.set_repository_content()

    async def set_repository_content(self):
        """Set repository content attributes."""
        contentfiles = []

        if self.content_path is None:
            first = await self.repository.get_contents("apps", self.ref)

            self.content_path = first[0].path

            self.name = first[0].name

        self.content_objects = await self.repository.get_contents(
            self.content_path, self.ref
        )

        if not isinstance(self.content_objects, list):
            raise HacsRequirement("Repository structure does not meet the requirements")

        for filename in self.content_objects:
            contentfiles.append(filename.name)

        if contentfiles:
            self.content_files = contentfiles
