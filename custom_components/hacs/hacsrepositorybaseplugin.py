"""Blueprint for HacsRepositoryPlugin."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
from datetime import datetime
import logging

from custom_components.hacs.blueprints import HacsRepositoryBase
from custom_components.hacs.exceptions import HacsBaseException, HacsMissingManifest

_LOGGER = logging.getLogger('custom_components.hacs.repository')


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

    def parse_readme_for_jstype(self):
        """Parse the readme looking for js type."""
        try:
            readme = self.repository.get_file_contents("README.md", self.ref)
            readme = readme.decoded_content.decode()
            for line in readme.splitlines():
                if "type: module" in line:
                    self.javascript_type = "module"
                    break
                elif "type: js" in line:
                    self.javascript_type = "js"
                    break
        except Exception:
            pass

    async def update(self):
        """Run update tasks."""
        try:
            if await self.common_update():
                return True
            self.parse_readme_for_jstype()
            if not self.set_repository_content():
                self.track = False

        except HacsBaseException as exception:
            raise HacsBaseException(exception)

        except Exception as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False
        else:
            self.track = True

        return True

    def set_repository_content(self):
        """Set repository content attributes."""
        if self.content_path is None or self.content_path == "":
            # Try fetching data from REPOROOT
            try:
                files = []
                objects = list(self.repository.get_dir_contents("", self.ref))
                for item in objects:
                    if item.name.endswith(".js"):
                        files.append(item.name)

                # Handler for plugin requirement 3
                find_file_name = "{}.js".format(self.name.replace("lovelace-", ""))
                if find_file_name in files:
                    # YES! We got it!
                    self.content_path = ""
                    self.content_objects = objects
                    self.content_files = files
                else:
                    _LOGGER.debug("Expected filename not found in %s for %s", files, self.repository_name)

            except Exception:
                pass

        if self.content_path is None or self.content_path == "release":
            # Try fetching data from Release
            try:
                files = []
                objects = list(self.last_release_object.get_assets())
                for item in objects:
                    if item.name.endswith(".js"):
                        files.append(item.name)

                # Handler for plugin requirement 3
                find_file_name1 = "{}.js".format(self.name)
                find_file_name2 = "{}-bundle.js".format(self.name)
                if find_file_name1 in files or find_file_name2 in files:
                    # YES! We got it!
                    self.content_path = "release"
                    self.content_objects = objects
                    self.content_files = files
                else:
                    _LOGGER.debug("Expected filename not found in %s for %s", files, self.repository_name)

            except Exception:
                pass

        if self.content_path is None or self.content_path == "dist":
            # Try fetching data from REPOROOT/dist
            try:
                files = []
                objects = list(self.repository.get_dir_contents("dist", self.ref))
                for item in objects:
                    if item.name.endswith(".js"):
                        files.append(item.name)

                # Handler for plug requirement 3
                find_file_name = "{}.js".format(self.name.replace("lovelace-", ""))
                if find_file_name in files:
                    # YES! We got it!
                    self.content_path = "dist"
                    self.content_objects = objects
                    self.content_files = files
                else:
                    _LOGGER.debug("Expected filename not found in %s for %s", files, self.repository_name)

            except Exception:
                pass

        if not self.content_files or not self.content_objects:
            raise HacsBaseException("No acceptable files found")
