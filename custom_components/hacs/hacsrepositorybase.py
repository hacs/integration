"""Blueprint for HacsRepositoryBase."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,wildcard-import
from asyncio import sleep
from datetime import datetime
import logging
import pathlib
import os
import shutil

from homeassistant.helpers.event import async_call_later

from custom_components.hacs.blueprints import HacsBase
from custom_components.hacs.exceptions import HacsRepositoryInfo, HacsUserScrewupException, HacsBaseException, HacsBlacklistException
from custom_components.hacs.handler.download import async_download_file, async_save_file

_LOGGER = logging.getLogger('custom_components.hacs.repository')


class HacsRepositoryBase(HacsBase):
    """HacsRepoBase Class"""

    def __init__(self):
        """Set up a HacsRepoBase object."""
        self.additional_info = None
        self.authors = None
        self.content_files = None
        self.content_objects = None
        self.content_path = None
        self.custom = False
        self.description = None
        self.hide = False
        self.installed = False
        self.last_release_object = None
        self.last_release_tag = None
        self.last_updated = None
        self.local_path = None
        self.name = None
        self.pending_restart = False
        self.ref = None
        self.releases = None
        self.repository = None
        self.repository_id = None
        self.repository_name = None
        self.repository_type = None
        self.show_beta = True
        self.track = True
        self.version_installed = None
        self.pending_update = bool(self.last_release_tag != self.version_installed)

    async def setup_repository(self):
        """
        Run initialation to setup a repository.

        Return True if everything is validated and ok.
        """
        try:
            # Check the blacklist
            if self.repository_name in self.blacklist or not self.track or self.hide:
                raise HacsBlacklistException

            # Set local path
            if self.local_path is None:

                if self.repository_type == "integration":
                    integration_name = self.repository_name.split("/")[-1]
                    self.local_path = f"{self.config_dir}/custom_components/{integration_name}"

                elif self.repository_type == "plugin":
                    self.local_path = f"{self.config_dir}/www/community/{self.name}"

            # Validate the repository name
            self.validate_repository_name()

            # Update repository info
            updateresult = await self.update(False)  # pylint: disable=no-member
            if not updateresult:
                self.track = False
                if self.repository_name not in self.blacklist:
                    self.blacklist.append(self.repository_name)
                _LOGGER.debug(f"({self.repository_name}) - Setup failed")
                return False

        except HacsBaseException as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False

        else:
            # If we get there all is good.
            self.start_task_scheduler()
            if str(self.repository_id) not in self.repositories:
                self.repositories[str(self.repository_id)] = self
            _LOGGER.debug(f"({self.repository_name}) - Setup of complete")

            return True

    def common_update(self):
        """Run common update tasks."""
        # Set the Gihub repository object
        self.set_repository()

        # Update description.
        self.set_description()

        # Set repository ID
        self.set_repository_id()

        # Set repository releases
        self.set_repository_releases()

        # Check if last updated string changed.
        current = self.last_updated
        new = self.return_last_update()
        if current == new and current is not None:
            return True
        self.last_updated = new

        # Set the repository ref
        self.set_ref()

        # Set additional info
        self.set_additional_info()

        # Run task later
        self.start_task_scheduler()


    async def download_repository_directory_content(self, repository_directory_path, local_directory, ref):
        """Download the content of a directory."""
        try:
            # Get content
            if self.content_path == "release":
                contents = self.content_objects
            else:
                contents = list(self.repository.get_dir_contents(repository_directory_path, ref))

            for content_object in contents:
                if content_object.type == "dir":
                    await self.download_repository_directory_content(content_object, local_directory, ref)
                if self.repository_type == "plugin" and not content_object.name.endswith(".js"):
                    continue

                _LOGGER.debug(f"Downloading {content_object.name}")

                if self.content_path == "release":
                    filecontent = await async_download_file(self.hass, content_object.browser_download_url)
                filecontent = await async_download_file(self.hass, content_object.download_url)

                if filecontent is None:
                    _LOGGER.debug(f"There was an error downloading the file {content_object.name}")
                    continue

                # Save the content of the file.
                local_file_path = f"{local_directory}/{content_object.name}"
                await async_save_file(local_file_path, filecontent)

        except Exception as exception:
            _LOGGER.debug(exception)

    def start_task_scheduler(self):
        """Start task scheduler."""
        if not self.installed:
            return

        # Update installed elements every 30min
        async_call_later(self.hass, 60*30, self.update)  # pylint: disable=no-member

    async def install(self):
        """Run install tasks."""
        start_time = datetime.now()
        _LOGGER.info(f'({self.repository_name}) - Starting installation')
        try:
            # Run update
            await self.update(False)  # pylint: disable=no-member

            # Check local directory
            await self.check_local_directory()

            # Download files
            await self.download_repository_directory_content(self.content_path, self.local_path, self.ref)

        except HacsBaseException as exception:
            _LOGGER.debug(f"({self.repository_name}) - {exception}")
            return False

        else:
            self.version_installed = self.last_release_tag
            self.installed = True
            if self.repository_type == "integration":
                self.pending_restart = True
            _LOGGER.info(f'({self.repository_name}) - installation completed in {(datetime.now() - start_time).seconds} seconds')


    async def remove(self):
        """Run remove tasks."""
        from custom_components.hacs.handler.storage import write_to_data_store
        _LOGGER.debug(f"({self.repository_name}) - Starting removal")

        await self.remove_local_directory()

        if self.repository_id in self.repositories:
            if not self.installed:
                del self.repositories[self.repository_id]

        if self.repository_name in self.data["custom"][self.repository_type]:
            self.data["custom"][self.repository_type].remove(self.repository_name)

        write_to_data_store(self.config_dir, self.data)



    async def uninstall(self):
        """Run uninstall tasks."""
        from custom_components.hacs.handler.storage import write_to_data_store
        _LOGGER.debug(f"({self.repository_name}) - Starting uninstall")
        await self.remove_local_directory()
        self.installed = False
        self.pending_restart = True
        self.version_installed = None
        if self.repository_name not in self.data["custom"][self.repository_type]:
            del self.repositories[self.repository_id]
        write_to_data_store(self.config_dir, self.data)

    async def check_local_directory(self):
        """Check the local directory."""
        try:
            # Remove if it's allready there.
            if os.path.exists(self.local_path):
                await self.remove_local_directory()

            # Create the new directory
            _LOGGER.debug(f"({self.repository_name}) - Creating {self.local_path}")
            pathlib.Path(self.local_path).mkdir(parents=True, exist_ok=True)

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

    def set_additional_info(self):
        """Add additional info (from info.md)."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")
        elif self.ref is None:
            raise HacsRepositoryInfo("GitHub repository ref is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = self.repository.get_file_contents("info.md", self.ref)
            temp = temp.decoded_content.decode()
            self.additional_info = temp

        except Exception:
            # We kinda expect this one to fail
            pass

    def set_custom(self):
        """Set the custom flag."""
        # Check if we need to run this.
        if self.custom is not None:
            return

        if self.repository_name is None:
            raise HacsRepositoryInfo("GitHub repository name is missing")

        # Assign to a temp var so we can check it before using it.
        temp = self.repository_name

        temp = temp.split("/")[0]

        if temp in ["custom-components", "csutom-cards"]:
            self.custom = False
        else:
            self.custom = True

    def set_description(self):
        """Set the custom flag."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp var so we can check it before using it.
        temp = self.repository.description

        if temp is not None:
            self.description = temp
        else:
            self.description = ""

    def set_repository(self):
        """Set the Github repository object."""
        # Check if we need to run this.
        if self.repository is not None:
            return

        if self.github is None:
            raise HacsRepositoryInfo("GitHub object is missing")
        elif self.repository_name is None:
            raise HacsRepositoryInfo("GitHub repository name is missing")

        # Assign to a temp var so we can check it before using it.
        temp = self.github.get_repo(self.repository_name)
        self.repository = temp


    def set_repository_id(self):
        """Set the ID of an repository."""
        # Check if we need to run this.
        if self.repository_id is not None:
            return

        if self.github is None:
            raise HacsRepositoryInfo("GitHub object is missing")
        elif self.repository_name is None:
            raise HacsRepositoryInfo("GitHub repository name is missing")
        elif self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp var so we can check it before using it.
        temp = self.repository.id

        if not isinstance(temp, int):
            raise TypeError(f"Value {temp} is not IntType.")
        self.repository_id = str(temp)


    def set_repository_releases(self):
        """Set attributes for releases."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp vars so we can check it before using it.
        temp = list(self.repository.get_releases())
        releases = []

        if temp:
            # Set info about the latest release.
            # Assign to a releasetemp var so we can check it before using it.
            releasetemp = temp[0]
            self.last_release_object = releasetemp
            self.last_release_tag = releasetemp.tag_name

            # Loop though the releases and add the .tag_name.
            for release in temp:
                releases.append(release.tag_name)

            # Check if out temp actually have content.
            if releases:
                self.releases = releases
            else:
                raise HacsRepositoryInfo("Github releases are missing")

    def set_ref(self):
        """Set repository ref to use."""
        # Check if we need to run this.
        if self.ref is not None:
            return

        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp vars so we can check it before using it.
        if self.last_release_tag is not None:
            temp = f"tags/{self.last_release_tag}"
        else:
            temp = self.repository.default_branch

        # We need this one so lets check it!
        if temp:
            if len(temp) < 1:
                raise HacsRepositoryInfo(
                    f"GitHub repository ref is wrong {temp}")

            elif not isinstance(temp, str):
                raise HacsRepositoryInfo(
                    f"GitHub repository ref is wrong {temp}")

            # Good! "tests" passed.
            else:
                self.ref = temp

    def validate_repository_name(self):
        """Validate the given repository_name."""
        if "/" not in self.repository_name:
            raise HacsUserScrewupException(
                "GitHub repository name "
                f"'{self.repository_name}' is not the correct format")

        elif len(self.repository_name.split('/')) > 2:
            raise HacsUserScrewupException(
                "GitHub repository name "
                f"'{self.repository_name}' is not the correct format")

    def return_last_update(self):
        """Return a last update string."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp var so we can check it before using it.
        if self.last_release_tag is not None:
            temp = self.last_release_object.created_at
        else:
            temp = self.repository.updated_at

        temp = temp.strftime("%d %b %Y %H:%M:%S")
