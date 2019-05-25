"""Blueprint for HacsRepositoryIntegration."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
from asyncio import sleep
from datetime import datetime
import logging
import json
import os
import shutil

from homeassistant.helpers.event import async_call_later
from custom_components.hacs.blueprints import HacsRepositoryBase
from custom_components.hacs.exceptions import HacsBaseException, HacsBlacklistException, HacsNotSoBasicException, HacsMissingManifest
from custom_components.hacs.handler.download import async_download_file, async_save_file

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

    async def check_local_directory(self):
        """Check the local directory."""
        try:
            # Remove if it's allready there.
            if os.path.exists(self.local_path):
                await self.remove_local_directory()

            # Create the new directory
            _LOGGER.debug(f"({self.repository_name}) - Creating {self.local_path}")
            os.mkdir(self.local_path)

        except Exception as exception:
            _LOGGER.debug(f"({self.repository_name}) - Creating directory {self.local_path} failed with {exception}")
            return

    async def remove_local_directory(self):
        """Check the local directory."""
        try:
            if os.path.exists(self.local_path):
                _LOGGER.debug(f"({self.repository_name}) - Removing {self.local_path}")
                shutil.rmtree(self.local_path)

                while os.path.exists(self.local_path):
                    _LOGGER.debug(f"({self.repository_name}) - {self.local_path} still exist, waiting 1s and checking again.")
                    await sleep(1)

        except Exception as exception:
            _LOGGER.debug(f"({self.repository_name}) - Removing directory {self.local_path} failed with {exception}")
            return

    async def setup_repository(self):
        """
        Run initialation to setup a repository.

        Return True if everything is validated and ok.
        """
        try:
            # Check the blacklist
            if self.repository_name in self.blacklist:
                raise HacsBlacklistException

            # If a previous attempt failed we need to reset the track flag
            self.track = True

            # Set local path
            if self.local_path is None:
                integration_name = self.repository_name.split("/")[-1]
                self.local_path = f"{self.config_dir}/custom_components/{integration_name}"

            # Validate the repository name
            self.validate_repository_name()
            #await sleep(0.2)

            # Update repository info
            updateresult = await self.update(False)
            if not updateresult:
                self.track = False
                self.hide = True
                if self.repository_name not in self.blacklist:
                    self.blacklist.append(self.repository_name)
                _LOGGER.debug(f"({self.repository_name}) - Setup failed")
                return False
            #await sleep(0.2)

        except HacsBaseException as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False

        else:
            # If we get there all is good.
            self.start_task_scheduler()
            if self.repository_id not in self.elements:
                self.elements[self.repository_id] = self
            _LOGGER.debug(f"({self.repository_name}) - Setup of complete")

            return True

    async def install(self):
        """Run install tasks."""
        start_time = datetime.now()
        _LOGGER.info(f'({self.repository_name}) - Starting installation')
        try:
            # Run update
            await self.update(False)
            #await sleep(0.2)

            # Check local directory
            await self.check_local_directory()
            #await sleep(0.2)

            # Download files
            for remote_file in self.content_objects:
                if remote_file.type == "dir":
                    continue
                _LOGGER.debug(f"({self.repository_name}) - Downloading {remote_file.path}")

                filecontent = await async_download_file(self.hass, remote_file.download_url)

                if filecontent is None:
                    _LOGGER.debug(f"({self.repository_name}) - There was an error downloading the file {remote_file.path}")
                    continue

                # Save the content of the file.
                local_file_path = f"{self.local_path}/{remote_file.name}"
                await async_save_file(local_file_path, filecontent)


        except HacsBaseException as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False

        else:
            self.version_installed = self.last_release_tag
            self.installed = True
            self.pending_restart = True
            _LOGGER.info(f'({self.repository_name}) - installation completed in {(datetime.now() - start_time).seconds} seconds')

    async def remove(self):
        """Run remove tasks."""

    async def uninstall(self):
        """Run uninstall tasks."""

    async def update(self, setup=False):
        """Run update tasks."""
        from custom_components.hacs.handler.storage import write_to_data_store
        if not setup:
            start_time = datetime.now()
            _LOGGER.info(f'({self.repository_name}) - Starting update')

        try:
            # Set the Gihub repository object
            self.set_repository()
            #await sleep(0.2)

            # Update description.
            self.set_description()
            #await sleep(0.2)

            # Set repository ID
            self.set_repository_id()
            #await sleep(0.2)

            # Set repository releases
            self.set_repository_releases()
            #await sleep(0.2)

            # Check if last updated string changed.
            current = self.last_updated
            new = self.return_last_update()
            if current == new and current is not None:
                return True
            self.last_updated = new

            # Set the repository ref
            self.set_ref()
            #await sleep(0.2)

            # Set additional info
            self.set_additional_info()
            #await sleep(0.2)

            # Set repository content
            self.set_repository_content()
            #await sleep(0.2)

            # Set manifest content
            self.set_manifest_content()
            #await sleep(0.2)

            # Run task later
            self.start_task_scheduler()

        except HacsBaseException as exception:
            raise HacsBaseException(exception)

        except Exception as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False

        if not setup:
            self.data[self.repository_id] = self
            write_to_data_store(self.config_dir, self.data)
            _LOGGER.info(f'({self.repository_name}) - update completed in {(datetime.now() - start_time).seconds} seconds')
        return True

    def start_task_scheduler(self):
        """Start task scheduler."""
        if not self.installed:
            return

        # Update installed elements every 30min
        async_call_later(self.hass, 60*30, self.update)

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
