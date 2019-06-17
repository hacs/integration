"""Blueprint for HacsRepositoryBase."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,wildcard-import,no-member
from asyncio import sleep
from datetime import datetime
import logging
import pathlib
import os
import shutil

from .aiogithub import AIOGitHubException
from .hacsbase import HacsBase
from .exceptions import (
    HacsRepositoryInfo,
    HacsUserScrewupException,
    HacsBaseException,
    HacsBlacklistException,
)
from .handler.download import async_download_file, async_save_file
from .const import DEFAULT_REPOSITORIES, VERSION

_LOGGER = logging.getLogger("custom_components.hacs.repository")


class HacsRepositoryBase(HacsBase):
    """HacsRepoBase Class"""

    def __init__(self):
        """Set up a HacsRepoBase object."""
        self.additional_info = None
        self.authors = None
        self.content_files = None
        self.content_objects = None
        self.content_path = None
        self.hide = False
        self.info = None
        self.installed = False
        self.installed_commit = None
        self.last_release_object = None
        self.last_release_tag = None
        self.last_updated = None
        self.name = None
        self.pending_restart = False
        self.reasons = []
        self.releases = None
        self.repository = None
        self.repository_name = None
        self.repository_type = None
        self.show_beta = True
        self.track = True
        self.version_installed = None

    @property
    def pending_update(self):
        """Return flag if the an update is pending."""
        if self.installed:
            if self.version_installed:
                return bool(self.last_release_tag != self.version_installed)
            else:
                return bool(self.installed_commit != self.last_commit)
        return False

    @property
    def custom(self):
        """Return flag if the repository is custom."""
        if self.repository_name.split("/")[0] in ["custom-components", "custom-cards"]:
            return False
        elif self.repository_name in DEFAULT_REPOSITORIES["integration"]:
            return False
        elif self.repository_name in DEFAULT_REPOSITORIES["plugin"]:
            return False
        return True

    @property
    def local_path(self):
        """Return local path."""
        local_path = None
        if self.repository_type == "integration":
            if self.domain is None:
                local_path = None
            else:
                local_path = "{}/custom_components/{}".format(
                    self.config_dir, self.domain
                )

        elif self.repository_type == "plugin":
            local_path = "{}/www/community/{}".format(self.config_dir, self.name)
        return local_path

    @property
    def topics(self):
        """Return repository topics."""
        return self.repository.topics

    @property
    def description(self):
        """Description."""
        return (
            "" if self.repository.description is None else self.repository.description
        )

    @property
    def ref(self):
        """Return the repository ref."""
        if self.last_release_tag is not None:
            return "tags/{}".format(self.last_release_tag)
        return self.repository.default_branch

    @property
    def repository_id(self):
        """Set the ID of an repository."""
        return str(self.repository.id)

    @property
    def last_commit(self):
        """Set the last commit of an repository."""
        return self.repository.last_commit

    async def setup_repository(self):
        """
        Run initialation to setup a repository.

        Return True if everything is validated and ok.
        """
        # Check the blacklist
        if self.repository_name in self.blacklist or not self.track:
            raise HacsBlacklistException

        # Hide HACS
        if self.repository_name == "custom-components/hacs":
            self.hide = True
            self.installed = True
            self.version_installed = VERSION

        # Validate the repository name
        await self.validate_repository_name()

        # Update repository info
        await self.update()  # pylint: disable=no-member

    async def common_update(self):
        """Run common update tasks."""
        # Check the blacklist
        if self.repository_name in self.blacklist or not self.track:
            raise HacsBlacklistException

        # Set the Gihub repository object
        await self.set_repository()

        # Set latest commit sha
        await self.repository.set_last_commit()

        # Set repository releases
        await self.set_repository_releases()

        # Check if last updated string changed.
        current = self.last_updated
        new = await self.return_last_update()
        if current == new and current is not None:
            return True
        self.last_updated = new

        try:
            # Set additional info
            await self.set_additional_info()
        except AIOGitHubException:
            pass

    async def download_repository_directory_content(
        self, repository_directory_path, local_directory, ref
    ):
        """Download the content of a directory."""
        try:
            # Get content
            if self.content_path == "release":
                contents = self.content_objects
            else:
                contents = await self.repository.get_contents(
                    repository_directory_path, ref
                )

            for content_object in contents:
                if content_object.type == "dir":
                    await self.download_repository_directory_content(
                        content_object.path, local_directory, ref
                    )
                    continue
                if (
                    self.repository_type == "plugin"
                    and not content_object.name.endswith(".js")
                ):
                    # For plugins we currently only need .js files
                    continue

                _LOGGER.debug("Downloading %s", content_object.name)

                filecontent = await async_download_file(
                    self.hass, content_object.download_url
                )

                if filecontent is None:
                    _LOGGER.debug(
                        "There was an error downloading the file %s",
                        content_object.name,
                    )
                    continue

                # Save the content of the file.
                if self.repository_name == "custom-components/hacs":
                    local_directory = "{}/{}".format(
                        self.config_dir, content_object.path
                    )
                    local_directory = local_directory.split(
                        "/{}".format(content_object.name)
                    )[0]
                    _LOGGER.debug(content_object.path)
                    _LOGGER.debug(local_directory)

                    # Check local directory
                    pathlib.Path(local_directory).mkdir(parents=True, exist_ok=True)

                local_file_path = "{}/{}".format(local_directory, content_object.name)
                await async_save_file(local_file_path, filecontent)

        except Exception as exception:
            raise HacsBaseException(exception)

    async def install(self):
        """Run install tasks."""
        start_time = datetime.now()
        _LOGGER.info("(%s) - Starting installation", self.repository_name)
        try:
            # Run update
            await self.update()  # pylint: disable=no-member

            # Check local directory
            await self.check_local_directory()

            # Download files
            await self.download_repository_directory_content(
                self.content_path, self.local_path, self.ref
            )

        except HacsBaseException as exception:
            _LOGGER.debug("(%s) - %s", self.repository_name, exception)
            return False

        else:
            self.version_installed = self.last_release_tag
            self.installed = True
            self.installed_commit = self.last_commit
            if self.repository_type == "integration":
                self.pending_restart = True
            _LOGGER.info(
                "(%s) - installation completed in %s seconds",
                self.repository_name,
                (datetime.now() - start_time).seconds,
            )

    async def remove(self):
        """Run remove tasks."""
        _LOGGER.debug("(%s) - Starting removal", self.repository_name)

        await self.remove_local_directory()

        if self.repository_id in self.repositories:
            if not self.installed:
                del self.repositories[self.repository_id]

    async def uninstall(self):
        """Run uninstall tasks."""
        _LOGGER.debug("(%s) - Starting uninstall", self.repository_name)
        await self.remove_local_directory()
        self.installed = False
        if self.repository_type == "integration":
            self.pending_restart = True
        self.version_installed = None

    async def check_local_directory(self, path=None):
        """Check the local directory."""
        try:
            if path is not None:
                local_path = path
            else:
                local_path = self.local_path

            # Remove if it's allready there.
            if os.path.exists(local_path):
                await self.remove_local_directory()

            # Create the new directory
            _LOGGER.debug("(%s) - Creating %s", self.repository_name, local_path)
            pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

        except Exception as exception:
            _LOGGER.debug(
                "(%s) - Creating directory %s failed with %s",
                self.repository_name,
                local_path,
                exception,
            )
            return

    async def remove_local_directory(self):
        """Check the local directory."""
        try:
            if os.path.exists(self.local_path):
                _LOGGER.debug(
                    "(%s) - Removing %s", self.repository_name, self.local_path
                )
                shutil.rmtree(self.local_path)

                while os.path.exists(self.local_path):
                    await sleep(1)

        except Exception as exception:
            _LOGGER.debug(
                "(%s) - Removing directory %s failed with %s",
                self.repository_name,
                self.local_path,
                exception,
            )
            return

    async def set_additional_info(self):
        """Add additional info (from info.md)."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")
        elif self.ref is None:
            raise HacsRepositoryInfo("GitHub repository ref is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = await self.repository.get_contents("info.md", self.ref)
            self.additional_info = temp.content

        except Exception:
            # We kinda expect this one to fail
            self.additional_info = ""

    async def set_repository(self):
        """Set the AIOGitHub repository object."""
        self.repository = await self.aiogithub.get_repo(self.repository_name)

    async def set_repository_releases(self):
        """Set attributes for releases."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp vars so we can check it before using it.
        temp = await self.repository.get_releases(True)

        if not temp:
            return

        self.last_release_object = temp
        self.last_release_tag = temp.tag_name

    async def validate_repository_name(self):
        """Validate the given repository_name."""
        if "/" not in self.repository_name:
            raise HacsUserScrewupException(
                "GitHub repository name "
                "'{}' is not the correct format".format(self.repository_name)
            )

        elif len(self.repository_name.split("/")) > 2:
            raise HacsUserScrewupException(
                "GitHub repository name "
                "'{}' is not the correct format".format(self.repository_name)
            )

    async def return_last_update(self):
        """Return a last update string."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp var so we can check it before using it.
        if self.last_release_tag is not None:
            temp = self.last_release_object.published_at
        else:
            temp = self.repository.pushed_at

        return temp.strftime("%d %b %Y %H:%M")
