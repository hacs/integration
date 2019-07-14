"""Blueprint for HacsRepositoryIntegration."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,access-member-before-definition
import logging
import json

from .hacsrepositorybase import HacsRepositoryBase
from ..hacsbase.exceptions import HacsRequirement

_LOGGER = logging.getLogger("custom_components.hacs.repository")


class HacsRepositoryIntegration(HacsRepositoryBase):
    """
    Set up a HacsRepositoryIntegration object.

    repository_name(str): The full name of a repository
    (example: awesome-dev/awesome-repo)
    """

    def __init__(self, repository_name: str, repositoryobject=None):
        """Initialize a HacsRepositoryIntegration object."""
        super().__init__()
        self.repository = repositoryobject
        self.repository_name = repository_name
        self.repository_type = "integration"
        self.manifest_content = None
        self.domain = None
        self.name = repository_name.split("/")[-1]

    @property
    def config_flow(self):
        """Return bool if integration has config_flow."""
        if self.manifest_content is None:
            return self.manifest_content.get("config_flow", False)
        return False

    async def reload_config_flows(self):
        """Reload config flows in HA."""

    async def update(self):
        """Run update tasks."""
        if await self.common_update():
            return
        await self.set_repository_content()
        await self.set_manifest_content()

    async def set_repository_content(self):
        """Set repository content attributes."""
        contentfiles = []

        if self.content_path is None:
            first = await self.repository.get_contents("custom_components", self.ref)

            self.content_path = first[0].path

        self.content_objects = await self.repository.get_contents(
            self.content_path, self.ref
        )

        if not isinstance(self.content_objects, list):
            raise HacsRequirement("Repository structure does not meet the requirements")

        for filename in self.content_objects:
            contentfiles.append(filename.name)

        if contentfiles:
            self.content_files = contentfiles

    async def set_manifest_content(self):
        """Set manifest content."""
        manifest_path = "{}/manifest.json".format(self.content_path)
        manifest = None

        if "manifest.json" not in self.content_files:
            raise HacsRequirement("manifest.json is missing.")

        manifest = await self.repository.get_contents(manifest_path, self.ref)
        manifest = json.loads(manifest.content)

        if manifest:
            self.manifest_content = manifest
            self.authors = manifest["codeowners"]
            self.name = manifest["name"]
            self.domain = manifest["domain"]
            self.homeassistant_version = manifest.get("homeassistant")
            return

        raise HacsRequirement("manifest.json does not contain expected values.")
