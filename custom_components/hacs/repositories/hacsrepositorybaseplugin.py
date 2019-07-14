"""Blueprint for HacsRepositoryPlugin."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,access-member-before-definition
import logging
import json

from .hacsrepositorybase import HacsRepositoryBase
from ..aiogithub.exceptions import AIOGitHubException
from ..hacsbase.exceptions import HacsRequirement

_LOGGER = logging.getLogger("custom_components.hacs.repository")


class HacsRepositoryPlugin(HacsRepositoryBase):
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
        self.repository_type = "plugin"
        self.manifest_content = None
        self.javascript_type = None
        self.name = repository_name.split("/")[-1]

    async def parse_readme_for_jstype(self):
        """Parse the readme looking for js type."""
        readme = None
        readme_files = ["readme", "readme.md"]
        root = await self.repository.get_contents("")
        for file in root:
            if file.name.lower() in readme_files:
                readme = await self.repository.get_contents(file.name)
                break

        if readme is None:
            return

        readme = readme.content
        for line in readme.splitlines():
            if "type: module" in line:
                self.javascript_type = "module"
                break
            elif "type: js" in line:
                self.javascript_type = "js"
                break

    async def update(self):
        """Run update tasks."""
        if await self.common_update():
            return
        try:
            await self.parse_readme_for_jstype()
        except AIOGitHubException:
            # This can fail, no big deal.
            pass

        await self.set_repository_content()

        try:
            await self.get_package_content()
        except AIOGitHubException:
            # This can fail, no big deal.
            pass


    async def set_repository_content(self):
        """Set repository content attributes."""
        if self.content_path is None or self.content_path == "dist":
            # Try fetching data from REPOROOT/dist
            try:
                files = []
                objects = await self.repository.get_contents("dist", self.ref)
                for item in objects:
                    if item.name.endswith(".js"):
                        files.append(item.name)

                # Handler for plug requirement 3
                find_file_name = "{}.js".format(self.name.replace("lovelace-", ""))
                if find_file_name in files or "{}.js".format(self.name) in files:
                    # YES! We got it!
                    self.content_path = "dist"
                    self.content_objects = objects
                    self.content_files = files

            except AIOGitHubException:
                pass

        if self.content_path is None or self.content_path == "release":
            # Try fetching data from Release
            try:
                files = []
                if self.last_release_object is not None:
                    if self.last_release_object.assets is not None:
                        for item in self.last_release_object.assets:
                            if item.name.endswith(".js"):
                                files.append(item.name)

                # Handler for plugin requirement 3
                find_file_name1 = "{}.js".format(self.name)
                find_file_name2 = "{}-bundle.js".format(self.name)
                if find_file_name1 in files or find_file_name2 in files:
                    # YES! We got it!
                    self.content_path = "release"
                    self.content_objects = self.last_release_object.assets
                    self.content_files = files

            except AIOGitHubException:
                pass

        if self.content_path is None or self.content_path == "":
            # Try fetching data from REPOROOT
            try:
                files = []
                objects = await self.repository.get_contents("", self.ref)
                for item in objects:
                    if item.name.endswith(".js"):
                        files.append(item.name)

                # Handler for plugin requirement 3
                find_file_name = "{}.js".format(self.name.replace("lovelace-", ""))
                if find_file_name in files or "{}.js".format(self.name) in files:
                    # YES! We got it!
                    self.content_path = ""
                    self.content_objects = objects
                    self.content_files = files

            except AIOGitHubException:
                pass

        if not self.content_files or not self.content_objects:
            raise HacsRequirement("No acceptable js files found")

    async def get_package_content(self):
        """Get package content."""
        package = None

        package = await self.repository.get_contents("package.json")
        package = json.loads(package.content)

        if package:
            self.authors = package["author"]
