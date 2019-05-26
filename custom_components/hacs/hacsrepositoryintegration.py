"""Blueprint for HacsRepositoryIntegration."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
from datetime import datetime
import logging
import json

from custom_components.hacs.blueprints import HacsRepositoryBase
from custom_components.hacs.exceptions import HacsBaseException, HacsMissingManifest

_LOGGER = logging.getLogger('custom_components.hacs.repository')


class HacsRepositoryIntegration(HacsRepositoryBase):
    """
    Set up a HacsRepositoryIntegration object.

    repository_name(str): The full name of a repository
    (example: awesome-dev/awesome-repo)
    """

    def __init__(self, repository_name: str):
        """Initialize a HacsRepositoryIntegration object."""
        super().__init__()
        self.repository_name = repository_name
        self.repository_type = "integration"
        self.manifest_content = None

    async def update(self, setup=False):
        """Run update tasks."""
        from custom_components.hacs.handler.storage import write_to_data_store
        if not setup:
            start_time = datetime.now()
            _LOGGER.info(f'({self.repository_name}) - Starting update')

        try:
            self.common_update()
            self.set_repository_content()
            self.set_manifest_content()

        except HacsBaseException as exception:
            raise HacsBaseException(exception)

        except Exception as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False

        if not setup:
            self.data[self.repository_id] = self
            await write_to_data_store(self.config_dir, self.data)
            _LOGGER.info(f'({self.repository_name}) - update completed in {(datetime.now() - start_time).seconds} seconds')
        return True

    def set_repository_content(self):
        """Set repository content attributes."""
        contentfiles = []

        if self.content_path is None:
            self.content_path = self.repository.get_dir_contents(
                "custom_components", self.ref)[0].path

        self.content_objects = list(self.repository.get_dir_contents(
            self.content_path, self.ref))

        for filename in self.content_objects:
            contentfiles.append(filename.name)

        if contentfiles:
            self.content_files = contentfiles

    def set_manifest_content(self):
        """Set manifest content."""
        manifest_path = "{}/manifest.json".format(self.content_path)
        manifest = None

        if "manifest.json" not in self.content_files:
            raise HacsMissingManifest

        manifest = self.repository.get_file_contents(manifest_path, self.ref)
        manifest = json.loads(manifest.decoded_content.decode())

        if manifest:
            self.manifest_content = manifest
            self.authors = manifest["codeowners"]
            self.name = manifest["name"]
