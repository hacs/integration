"""Blueprint for HacsRepositoryPythonScripts."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,access-member-before-definition
import logging

from .hacsrepositorybase import HacsRepositoryBase
from ..hacsbase.exceptions import HacsRequirement

_LOGGER = logging.getLogger("custom_components.hacs.repository")


class HacsRepositoryPythonScripts(HacsRepositoryBase):
    """
    Set up a HacsRepositoryPythonScripts object.

    repository_name(str): The full name of a repository
    (example: awesome-dev/awesome-repo)
    """

    def __init__(self, repository_name: str, repositoryobject=None):
        """Initialize a HacsRepositoryPythonScripts object."""
        super().__init__()
        self.repository = repositoryobject
        self.repository_name = repository_name
        self.repository_type = "python_script"
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
            self.content_objects = await self.repository.get_contents(
                "python_scripts", self.ref
            )

            self.content_path = self.content_objects[0].path

            self.name = self.content_objects[0].name.replace(".py", "")

        if not isinstance(self.content_objects, list):
            raise HacsRequirement("Repository structure does not meet the requirements")

        for filename in self.content_objects:
            contentfiles.append(filename.name)

        if contentfiles:
            self.content_files = contentfiles
